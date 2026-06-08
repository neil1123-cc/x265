#!/usr/bin/env python3
import importlib.util
import io
import runpy
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

_MAIN_CACHE = {}


def script_main(script, module_name=None):
    script = Path(script).resolve()
    main_func = _MAIN_CACHE.get(script)
    if main_func is not None:
        return main_func

    spec = importlib.util.spec_from_file_location(module_name or f'_ci_guard_{script.stem}', script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load checker: {script}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    main_func = getattr(module, 'main', None)
    if main_func is None:
        def run_as_script():
            runpy.run_path(str(script), run_name='__main__')
        main_func = run_as_script
    _MAIN_CACHE[script] = main_func
    return main_func


def run_python_script_main(script, args=(), module_name=None):
    script = Path(script)
    stdout = io.StringIO()
    stderr = io.StringIO()
    old_argv = sys.argv
    exit_code = 0
    try:
        sys.argv = [str(script), *(str(arg) for arg in args)]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            script_main(script, module_name)()
    except SystemExit as exc:
        if isinstance(exc.code, int):
            exit_code = exc.code
        elif exc.code is None:
            exit_code = 0
        else:
            exit_code = 1
            print(exc.code, file=stderr)
    finally:
        sys.argv = old_argv
    return SimpleNamespace(returncode=exit_code, stdout=stdout.getvalue() + stderr.getvalue())
