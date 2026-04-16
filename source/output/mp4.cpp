#include "mp4.h"

#if _WIN32
#include <windows.h>
#endif

#define NALU_LENGTH_SIZE 4

static inline int x265_is_regular_file_path(const char *path)
{
#if _WIN32
    int ret = -1;
    wchar_t path_utf16[MAX_PATH * 2];
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, path_utf16, sizeof(path_utf16) / sizeof(wchar_t)))
    {
        struct _stati64 file_stat;
        ret = !(WaitNamedPipeW(path_utf16, 0) || GetLastError() == ERROR_SEM_TIMEOUT);
        if (ret && !_wstati64(path_utf16, &file_stat))
            ret = S_ISREG(file_stat.st_mode);
    }
    return ret;
#else
    struct stat file_stat;
    if (stat(path, &file_stat))
        return 1;
    return S_ISREG(file_stat.st_mode);
#endif
}

typedef struct
{
    int64_t start;
    int no_progress;
} remux_cb_param;

static inline int x265_is_regular_file(FILE *filehandle)
{
    struct stat file_stat;
    if (fstat(fileno(filehandle), &file_stat))
        return 1;
    return S_ISREG(file_stat.st_mode);
}

/*******************/

#define MP4_LOG_ERROR( ... )                general_log( NULL, "mp4", X265_LOG_ERROR, __VA_ARGS__ )
#define MP4_FAIL_IF_ERR MP4_LOG_IF_ERR

/* For close_file() */
#define MP4_LOG_IF_ERR( cond, ... )\
if( cond )\
{\
    MP4_LOG_ERROR( __VA_ARGS__ );\
    b_fail = true;\
}

/* For open_file() */
#define MP4_FAIL_IF_ERR_EX( cond, ... )\
if( cond )\
{\
    remove_mp4_hnd();\
    MP4_LOG_ERROR( __VA_ARGS__ );\
    b_fail = true;\
    return -1;\
}

/*******************/

using namespace X265_NS;
using namespace std;

int remux_callback(void *param, uint64_t done, uint64_t total)
{
    remux_cb_param *cb_param = (remux_cb_param *)param;
    if (cb_param->no_progress && done != total)
        return 0;
    int64_t elapsed = x265_mdate() - cb_param->start;
    double byterate = done / (elapsed / 1000000.);
    fprintf(stderr, "remux [%5.2lf%%], %" PRIu64 "/%" PRIu64 " KiB, %u KiB/s, ",
            done * 100. / total, done / 1024, total / 1024, (unsigned)byterate / 1024);
    if (done == total)
    {
        unsigned sec = (unsigned)(elapsed / 1000000);
        fprintf(stderr, "total elapsed %u:%02u:%02u\n\n", sec / 3600, (sec / 60) % 60, sec % 60);
    }
    else
    {
        unsigned eta = (unsigned)((total - done) / byterate);
        fprintf(stderr, "eta %u:%02u:%02u\r", eta / 3600, (eta / 60) % 60, eta % 60);
    }
    fflush(stderr);
    return 0;
}

void MP4Output::FixTimeScale(uint64_t &i_media_timescale) {
    old_timescale = 0;
    return; /* Until we have VFR support */

    if (fpsNum == 0 || i_media_timescale % fpsNum == 0 || fpsDenom % 1001 != 0) {
        old_timescale = 0;
        return;
    }
    old_timescale = i_media_timescale;
    old_time_inc = i_time_inc;
    i_time_inc = 1;
    i_media_timescale = fpsNum;
    fpsScale = fpsDenom / 1001;
}

#define MAX_OFFSET 50 // 5% offset

int64_t MP4Output::GetTimeScaled(int64_t xts) {
    if (old_timescale == 0)
        return xts;
    xts = xts * i_video_timescale / old_timescale;
    int64_t offset = (xts + MAX_OFFSET * fpsScale) % fpsDenom;
    if (offset <= MAX_OFFSET * 2 * fpsScale)
        xts -= offset - MAX_OFFSET * fpsScale;
    return xts;
}

void MP4Output::remove_mp4_hnd()
{
    if (summary)
    {
        lsmash_cleanup_summary((lsmash_summary_t *)summary);
        summary = NULL;
    }
    if (p_root)
    {
        lsmash_close_file(&file_param);
        lsmash_destroy_root(p_root);
        p_root = NULL;
    }
    delete[] p_sei_buffer;
    p_sei_buffer = NULL;
    i_sei_size = 0;
}

/*******************/

void MP4Output::sign()
{
    /* Write a tag in a free space to indicate the output file is written by L-SMASH. */
    const char *string = "Multiplexed by L-SMASH";
    int   length = strlen(string);
    lsmash_box_type_t type = lsmash_form_iso_box_type(LSMASH_4CC('f', 'r', 'e', 'e'));
    lsmash_box_t *free_box = lsmash_create_box(type, (uint8_t *)string, length, LSMASH_BOX_PRECEDENCE_N);
    if(!free_box)
        return;
    if(lsmash_add_box_ex(lsmash_root_as_box(p_root), &free_box) < 0)
    {
        lsmash_destroy_box(free_box);
        return;
    }
    lsmash_write_top_level_box(free_box);
}

void MP4Output::closeFile(int64_t largest_pts, int64_t second_largest_pts)
{
    if(p_root)
    {
        double actual_duration = 0;
        uint32_t last_delta = 0;
        general_log(NULL, "mp4", X265_LOG_INFO,
                    "closeFile root=%p track=%u frames=%d fragments=%d stdout=%d largest_pts=%lld second_largest_pts=%lld first_cts=%" PRIu64 " time_inc=%" PRIu64 " video_ts=%u movie_ts=%u\n",
                    p_root, i_track, i_numframe, b_fragments, b_stdout,
                    (long long)largest_pts, (long long)second_largest_pts, i_first_cts,
                    i_time_inc, i_video_timescale, i_movie_timescale);
        if(i_track)
        {
            /* Flush the rest of samples and add the last sample_delta. */
            last_delta = largest_pts - second_largest_pts;
            int flush_ret = lsmash_flush_pooled_samples(p_root, i_track, GetTimeScaled((last_delta ? last_delta : 1) * i_time_inc));
            general_log(NULL, "mp4", X265_LOG_INFO,
                        "closeFile flush_ret=%d last_delta=%u scaled_delta=%lld\n",
                        flush_ret, last_delta,
                        (long long)GetTimeScaled((last_delta ? last_delta : 1) * i_time_inc));
            MP4_LOG_IF_ERR(flush_ret,
                           "failed to flush the rest of samples.\n");

            if(i_movie_timescale != 0 && i_video_timescale != 0)      /* avoid zero division */
                actual_duration = ((double)GetTimeScaled((largest_pts + last_delta) * i_time_inc) / i_video_timescale) * i_movie_timescale;
            else
                MP4_LOG_ERROR("timescale is broken.\n");
            general_log(NULL, "mp4", X265_LOG_INFO,
                        "closeFile actual_duration=%.3f scaled_end=%lld\n",
                        actual_duration,
                        (long long)GetTimeScaled((largest_pts + last_delta) * i_time_inc));

            /*
             * Declare the explicit time-line mapping.
             * A segment_duration is given by movie timescale, while a media_time that is the start time of this segment
             * is given by not the movie timescale but rather the media timescale.
             * The reason is that ISO media have two time-lines, presentation and media time-line,
             * and an edit maps the presentation time-line to the media time-line.
             * According to QuickTime file format specification and the actual playback in QuickTime Player,
             * if the Edit Box doesn't exist in the track, the ratio of the summation of sample durations and track's duration becomes
             * the track's media_rate so that the entire media can be used by the track.
             * So, we add Edit Box here to avoid this implicit media_rate could distort track's presentation timestamps slightly.
             * Note: Any demuxers should follow the Edit List Box if it exists.
             */
            lsmash_edit_t edit;
            edit.duration   = actual_duration;
            edit.start_time = i_first_cts;
            edit.rate       = ISOM_EDIT_MODE_NORMAL;
            if (!b_fragments)
            {
                int map_ret = lsmash_create_explicit_timeline_map(p_root, i_track, edit);
                general_log(NULL, "mp4", X265_LOG_INFO,
                            "closeFile create_timeline_ret=%d duration=%.3f start=%" PRIu64 "\n",
                            map_ret, actual_duration, i_first_cts);
                MP4_LOG_IF_ERR(map_ret,
                               "failed to set timeline map for video.\n");
            }
            else if (!b_stdout)
            {
                int map_ret = lsmash_modify_explicit_timeline_map(p_root, i_track, 1, edit);
                general_log(NULL, "mp4", X265_LOG_INFO,
                            "closeFile modify_timeline_ret=%d duration=%.3f start=%" PRIu64 "\n",
                            map_ret, actual_duration, i_first_cts);
                MP4_LOG_IF_ERR(map_ret,
                               "failed to update timeline map for video.\n");
            }
        }

        remux_cb_param cb_param;
        cb_param.no_progress = 1;
        cb_param.start = x265_mdate();
        lsmash_adhoc_remux_t remux_info;
        remux_info.func = remux_callback;
        remux_info.buffer_size = 4 * 1024 * 1024;
        remux_info.param = &cb_param;
        int finish_ret = lsmash_finish_movie(p_root, &remux_info);
        general_log(NULL, "mp4", X265_LOG_INFO,
                    "closeFile finish_movie_ret=%d fragments=%d stdout=%d frames=%d\n",
                    finish_ret, b_fragments, b_stdout, i_numframe);
        MP4_LOG_IF_ERR(finish_ret, "failed to finish movie.\n");
    }

    sign();

    remove_mp4_hnd(); /* including lsmash_destroy_root( p_root ); */
}

int MP4Output::openFile(const char *psz_filename)
{
    int b_regular = strcmp(psz_filename, "-");
    b_regular = b_regular && x265_is_regular_file_path(psz_filename);
    if (b_regular)
    {
        FILE *fh = x265_fopen(psz_filename, "wb");
        MP4_FAIL_IF_ERR_EX(!fh, "cannot open output file `%s'.\n", psz_filename);
        b_regular = x265_is_regular_file(fh);
        fclose(fh);
    }

    b_stdout = !strcmp(psz_filename, "-");
    b_fragments = !b_regular;
    general_log(NULL, "mp4", X265_LOG_INFO, "openFile regular=%d stdout=%d fragments=%d file=%s\n",
                b_regular, b_stdout, b_fragments, psz_filename);

    p_root = lsmash_create_root();
    MP4_FAIL_IF_ERR_EX(!p_root, "failed to create root.\n");

    MP4_FAIL_IF_ERR_EX(lsmash_open_file(psz_filename, 0, &file_param) < 0, "failed to open an output file.\n");
    if (b_fragments)
        file_param.mode = static_cast<lsmash_file_mode>(file_param.mode | LSMASH_FILE_MODE_FRAGMENTED);

    summary = (lsmash_video_summary_t *)lsmash_create_summary(LSMASH_SUMMARY_TYPE_VIDEO);
    MP4_FAIL_IF_ERR_EX(!summary,
                       "failed to allocate memory for summary information of video.\n");
    summary->sample_type = ISOM_CODEC_TYPE_HVC1_VIDEO;

    return 0;
}

void MP4Output::setParam(x265_param *p_param)
{
    p_param->bAnnexB = false;
    p_param->bRepeatHeaders = false;

    x265Param = p_param;
    uint64_t i_media_timescale;
    i_numframe = 0;
    i_delay_frames = p_param->bframes ? (p_param->bBPyramid ? 2 : 1) : 0;

    i_media_timescale = (uint64_t)info.timebaseDenom;
    i_time_inc = (uint64_t)info.timebaseNum;
    general_log(p_param, "mp4", X265_LOG_DEBUG, "Input Timebase: %lld/%lld\n", i_time_inc, i_media_timescale);
    fpsNum = p_param->fpsNum;
    fpsDenom = p_param->fpsDenom;
    FixTimeScale(i_media_timescale);
    general_log(p_param, "mp4", X265_LOG_DEBUG, "Fixed Timebase: %lld/%lld\n", i_time_inc, i_media_timescale);
    MP4_FAIL_IF_ERR(i_media_timescale > UINT32_MAX, "MP4 media timescale %" PRIu64 " exceeds maximum\n", i_media_timescale);

    /* Select brands. */
    lsmash_brand_type brands[6] = { static_cast<lsmash_brand_type>(0) };
    uint32_t brand_count = 0;
    brands[brand_count++] = ISOM_BRAND_TYPE_MP42;
    brands[brand_count++] = ISOM_BRAND_TYPE_MP41;
    brands[brand_count++] = ISOM_BRAND_TYPE_ISOM;

    /* Set file */
    lsmash_file_parameters_t *fparam = &file_param;
    fparam->major_brand   = brands[0];
    fparam->brands        = brands;
    fparam->brand_count   = brand_count;
    fparam->minor_version = 0;
    MP4_FAIL_IF_ERR(!lsmash_set_file(p_root, fparam), "failed to add an output file into a ROOT.\n");

    /* Set movie parameters. */
    lsmash_movie_parameters_t movie_param;
    lsmash_initialize_movie_parameters(&movie_param);
    MP4_FAIL_IF_ERR(lsmash_set_movie_parameters(p_root, &movie_param),
                    "failed to set movie parameters.\n");
    i_movie_timescale = lsmash_get_movie_timescale(p_root);
    MP4_FAIL_IF_ERR(!i_movie_timescale, "movie timescale is broken.\n");

    /* Create a video track. */
    i_track = lsmash_create_track(p_root, ISOM_MEDIA_HANDLER_TYPE_VIDEO_TRACK);
    MP4_FAIL_IF_ERR(!i_track, "failed to create a video track.\n");

    summary->width = p_param->sourceWidth;
    summary->height = p_param->sourceHeight;
    uint32_t i_display_width = p_param->sourceWidth << 16;
    uint32_t i_display_height = p_param->sourceHeight << 16;
    if(p_param->vui.sarWidth && p_param->vui.sarHeight)
    {
        double sar = (double)p_param->vui.sarWidth / p_param->vui.sarHeight;
        if(sar > 1.0)
            i_display_width *= sar;
        else
            i_display_height /= sar;
        summary->par_h = p_param->vui.sarWidth;
        summary->par_v = p_param->vui.sarHeight;
    }
    summary->color.primaries_index = p_param->vui.colorPrimaries;
    summary->color.transfer_index  = p_param->vui.transferCharacteristics;
    summary->color.matrix_index    = p_param->vui.matrixCoeffs >= 0 ? p_param->vui.matrixCoeffs : ISOM_MATRIX_INDEX_UNSPECIFIED;
    summary->color.full_range      = p_param->vui.bEnableVideoFullRangeFlag >= 0 ? p_param->vui.bEnableVideoFullRangeFlag : 0;

    /* Set video track parameters. */
    lsmash_track_parameters_t track_param;
    lsmash_initialize_track_parameters(&track_param);
    lsmash_track_mode track_mode = static_cast<lsmash_track_mode>(ISOM_TRACK_ENABLED | ISOM_TRACK_IN_MOVIE | ISOM_TRACK_IN_PREVIEW);
    track_param.mode = track_mode;
    track_param.display_width = i_display_width;
    track_param.display_height = i_display_height;
    MP4_FAIL_IF_ERR(lsmash_set_track_parameters(p_root, i_track, &track_param),
                    "failed to set track parameters for video.\n");

    /* Set video media parameters. */
    lsmash_media_parameters_t media_param;
    lsmash_initialize_media_parameters(&media_param);
    media_param.timescale = i_media_timescale;
    media_param.media_handler_name = strdup("L-SMASH Video Media Handler");
    MP4_FAIL_IF_ERR(lsmash_set_media_parameters(p_root, i_track, &media_param),
                    "failed to set media parameters for video.\n");
    i_video_timescale = lsmash_get_media_timescale(p_root, i_track);
    MP4_FAIL_IF_ERR(!i_video_timescale, "media timescale for video is broken.\n");
}

/* p_nal = VPS, SPS, PPS[, SEIUserData]
 * VPS, SPS and PPS will be appended by `lsmash_append_hevc_dcr_nalu`
 * SEIUserData will be saved and appended to the first frame later
 * [out] p_sei_buffer: buffer contains SEIUserData NALU prefix'd by 4 byte length
 * [out] i_sei_size:   size of p_sei_buffer
 */
int MP4Output::writeHeaders(const x265_nal* p_nal, uint32_t nalcount)
{
    MP4_FAIL_IF_ERR(nalcount < 3, "header should contain 3+ nals");
    uint32_t vps_size = p_nal[0].sizeBytes - NALU_LENGTH_SIZE;
    uint32_t sps_size = p_nal[1].sizeBytes - NALU_LENGTH_SIZE;
    uint32_t pps_size = p_nal[2].sizeBytes - NALU_LENGTH_SIZE;

    uint8_t *vps = p_nal[0].payload + NALU_LENGTH_SIZE;
    uint8_t *sps = p_nal[1].payload + NALU_LENGTH_SIZE;
    uint8_t *pps = p_nal[2].payload + NALU_LENGTH_SIZE;

    lsmash_codec_specific_t *cs = lsmash_create_codec_specific_data(LSMASH_CODEC_SPECIFIC_DATA_TYPE_ISOM_VIDEO_HEVC,
                                  LSMASH_CODEC_SPECIFIC_FORMAT_STRUCTURED);

    lsmash_hevc_specific_parameters_t *param = (lsmash_hevc_specific_parameters_t *)cs->data.structured;
    param->lengthSizeMinusOne = NALU_LENGTH_SIZE - 1;

    /* VPS */
    if(lsmash_append_hevc_dcr_nalu(param, HEVC_DCR_NALU_TYPE_VPS, vps, vps_size))
    {
        MP4_LOG_ERROR("failed to append VPS.\n");
        b_fail = true;
        return -1;
    }

    /* SPS */
    if(lsmash_append_hevc_dcr_nalu(param, HEVC_DCR_NALU_TYPE_SPS, sps, sps_size))
    {
        MP4_LOG_ERROR("failed to append SPS.\n");
        b_fail = true;
        return -1;
    }

    /* PPS */
    if(lsmash_append_hevc_dcr_nalu(param, HEVC_DCR_NALU_TYPE_PPS, pps, pps_size))
    {
        MP4_LOG_ERROR("failed to append PPS.\n");
        b_fail = true;
        return -1;
    }

    if(lsmash_add_codec_specific_data((lsmash_summary_t *)summary, cs))
    {
        MP4_LOG_ERROR("failed to add H.264 specific info.\n");
        return -1;
    }

    lsmash_destroy_codec_specific_data(cs);

    i_sample_entry = lsmash_add_sample_entry(p_root, i_track, summary);
    MP4_FAIL_IF_ERR(!i_sample_entry,
                    "failed to add sample entry for video.\n");

    i_sei_size = 0;
    if(nalcount >= 4)
    {
        for (uint32_t i = 3; i < nalcount; i++)
            i_sei_size += p_nal[i].sizeBytes;

        /* SEI */
        p_sei_buffer = new uint8_t[i_sei_size];
        MP4_FAIL_IF_ERR(!p_sei_buffer,
                        "failed to allocate sei transition buffer.\n");

        uint8_t *p_sei_pt = p_sei_buffer;
        for (uint32_t i = 3; i < nalcount; i++)
        {
            memcpy(p_sei_pt, p_nal[i].payload, p_nal[i].sizeBytes);
            p_sei_pt += p_nal[i].sizeBytes;
        }
    }

    return vps_size + sps_size + pps_size;
}

/* p_nalu = [SEI, ]Frame
 * `[start code] NALU` converted to `[length] NALU`, concatenated and put into a sample
 */
int MP4Output::writeFrame(const x265_nal* p_nalu, uint32_t nalcount, x265_picture& pic)
{
    const bool b_keyframe = pic.sliceType == X265_TYPE_IDR;
    int i_size = 0;
    const int64_t i_pts = pic.pts;
    const int64_t i_dts = pic.dts;
    uint64_t dts, cts;
    general_log(x265Param, "mp4", X265_LOG_DEBUG, "Write Frame: DTS: %8lld  PTS: %8lld\n", pic.dts, pic.pts);

    if(!i_numframe)
    {
        i_start_offset = i_dts * -1;
        i_first_cts = GetTimeScaled(i_start_offset * i_time_inc);
        if (b_fragments)
        {
            lsmash_edit_t edit;
            edit.duration = ISOM_EDIT_DURATION_UNKNOWN32;
            edit.start_time = i_first_cts;
            edit.rate = ISOM_EDIT_MODE_NORMAL;
            MP4_LOG_IF_ERR(lsmash_create_explicit_timeline_map(p_root, i_track, edit),
                           "failed to set timeline map for video.\n");
        }
    }

    for(uint8_t i = 0; i < nalcount; i++)
        i_size += p_nalu[i].sizeBytes;
    i_size += i_sei_size;
    lsmash_sample_t *p_sample = lsmash_create_sample(i_size);
    MP4_FAIL_IF_ERR(!p_sample,
                    "failed to create a video sample data.\n");

    uint8_t* pp = p_sample->data;
    if(p_sei_buffer)
    {
        memcpy(pp, p_sei_buffer, i_sei_size);
        pp += i_sei_size;
        delete[] p_sei_buffer;
        p_sei_buffer = NULL;
        i_sei_size = 0;
    }
    for(uint8_t i = 0; i < nalcount; i++)
    {
        // Length of NAL header
        int size = p_nalu[i].sizeBytes;
        memcpy(pp, p_nalu[i].payload, size);
        pp += size;
    }

    dts = GetTimeScaled((i_dts + i_start_offset) * i_time_inc);
    cts = GetTimeScaled((i_pts + i_start_offset) * i_time_inc);

    p_sample->dts = dts;
    p_sample->cts = cts;
    p_sample->index = i_sample_entry;
    p_sample->prop.ra_flags = b_keyframe ? ISOM_SAMPLE_RANDOM_ACCESS_FLAG_SYNC : ISOM_SAMPLE_RANDOM_ACCESS_FLAG_NONE;

    if (b_fragments && i_numframe && p_sample->prop.ra_flags != ISOM_SAMPLE_RANDOM_ACCESS_FLAG_NONE)
    {
        MP4_FAIL_IF_ERR(lsmash_flush_pooled_samples(p_root, i_track, p_sample->dts - i_prev_dts),
                        "failed to flush the rest of samples.\n");
        MP4_FAIL_IF_ERR(lsmash_create_fragment_movie(p_root),
                        "failed to create a movie fragment.\n");
    }

    /* Append data per sample. */
    MP4_FAIL_IF_ERR(lsmash_append_sample(p_root, i_track, p_sample),
                    "failed to append a video frame.\n");

    i_prev_dts = dts;
    i_numframe++;

    return i_size;
}
