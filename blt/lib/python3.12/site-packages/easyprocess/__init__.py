"""Easy to use python subprocess interface."""
import logging
import os.path
import subprocess
import tempfile
import time
from typing import Any, List, Optional, Union

from easyprocess.about import __version__
from easyprocess.unicodeutil import split_command, unidecode

log = logging.getLogger(__name__)

log.debug("version=%s", __version__)


class EasyProcessError(Exception):
    def __init__(self, easy_process, msg=""):
        self.easy_process = easy_process
        self.msg = msg

    def __str__(self):
        return self.msg + " " + repr(self.easy_process)


def _rm_ending_lf(s):
    if s.endswith("\n"):
        s = s[:-1]
    if s.endswith("\r"):
        s = s[:-1]
    return s


class EasyProcess(object):

    """
    .. module:: easyprocess

    simple interface for :mod:`subprocess`

    shell is not supported (shell=False)

    .. warning::

      unicode is supported only for string list command (Python2.x)
      (check :mod:`shlex` for more information)

    :param cmd: string ('ls -l') or list of strings (['ls','-l'])
    :param cwd: working directory
    :param use_temp_files: use temp files (True) or pipes (False) for stdout and stderr,
                           pipes can cause deadlock in some cases (see unit tests)

    :param env: If *env* is not ``None``, it must be a mapping that defines the environment
                   variables for the new process; these are used instead of inheriting the current
                   process' environment, which is the default behavior.
                   (check :mod:`subprocess`  for more information)
    """

    def __init__(
        self,
        cmd: Union[List[str], str],
        cwd: Optional[str] = None,
        use_temp_files: bool = True,
        env=None,
    ):
        self.use_temp_files = use_temp_files
        # for testing
        EASYPROCESS_USE_TEMP_FILES = os.environ.get("EASYPROCESS_USE_TEMP_FILES")
        if EASYPROCESS_USE_TEMP_FILES:
            log.debug("EASYPROCESS_USE_TEMP_FILES=%s", EASYPROCESS_USE_TEMP_FILES)
            # '0'->false, '1'->true
            self.use_temp_files = bool(int(EASYPROCESS_USE_TEMP_FILES))

        self._outputs_processed = False

        self.env = env
        self.popen: Optional[subprocess.Popen] = None
        self.stdout = None
        self.stderr = None
        self._stdout_file: Any = None
        self._stderr_file: Any = None
        self.is_started = False
        self.oserror: Optional[OSError] = None
        self.cmd_param = cmd
        # self._thread: Optional[threading.Thread] = None
        self.timeout_happened = False
        self.cwd = cwd
        self.cmd = split_command(cmd)
        # self.cmd_as_string = " ".join(self.cmd)
        self.enable_stdout_log = True
        self.enable_stderr_log = True

        # log.debug('param: "%s" ', self.cmd_param)
        log.debug("command: %s", self.cmd)
        # log.debug('joined command: %s', self.cmd_as_string)

        if not len(self.cmd):
            raise EasyProcessError(self, "empty command!")

    def __repr__(self):
        msg = '<%s cmd_param=%s cmd=%s oserror=%s return_code=%s stdout="%s" stderr="%s" timeout_happened=%s>' % (
            self.__class__.__name__,
            self.cmd_param,
            self.cmd,
            self.oserror,
            self.return_code,
            self.stdout,
            self.stderr,
            self.timeout_happened,
        )
        return msg

    @property
    def pid(self) -> Optional[int]:
        """
        PID (:attr:`subprocess.Popen.pid`)

        :rtype: int
        """
        if self.popen:
            return self.popen.pid
        return None

    @property
    def return_code(self) -> Optional[int]:
        """
        returncode (:attr:`subprocess.Popen.returncode`)

        :rtype: int
        """
        if self.popen:
            return self.popen.returncode
        return None

    def call(self, timeout: Optional[float] = None) -> "EasyProcess":
        """Run command with arguments. Wait for command to complete.

        same as:
         1. :meth:`start`
         2. :meth:`wait`
         3. :meth:`stop`

        :rtype: self

        """
        try:
            self.start().wait(timeout=timeout)
        finally:
            if self.is_alive():
                self.stop()
        return self

    def start(self) -> "EasyProcess":
        """start command in background and does not wait for it.

        :rtype: self

        """
        if self.is_started:
            raise EasyProcessError(self, "process was started twice!")

        stdout: Any = None
        stderr: Any = None
        if self.use_temp_files:
            self._stdout_file = tempfile.TemporaryFile(prefix="stdout_")
            self._stderr_file = tempfile.TemporaryFile(prefix="stderr_")
            stdout = self._stdout_file
            stderr = self._stderr_file

        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE
        # cmd = list(map(uniencode, self.cmd))

        try:
            self.popen = subprocess.Popen(
                self.cmd,
                stdout=stdout,
                stderr=stderr,
                cwd=self.cwd,
                env=self.env,
            )
        except OSError as oserror:
            log.debug("OSError exception: %s", oserror)
            self.oserror = oserror
            raise EasyProcessError(self, "start error")
        self.is_started = True
        log.debug("process was started (pid=%s)", self.pid)
        return self

    def is_alive(self) -> bool:
        """
        poll process using :meth:`subprocess.Popen.poll`
        It updates stdout/stderr/return_code if process has stopped earlier.

        :rtype: bool
        """
        if self.popen:
            alive = self.popen.poll() is None

            if not alive:
                # collect stdout/stderr/return_code if proc stopped
                self._wait4process()

            return alive
        else:
            return False

    def wait(self, timeout: Optional[float] = None) -> "EasyProcess":
        """Wait for command to complete.

        :rtype: self

        """
        # Timeout (threading) discussion: https://stackoverflow.com/questions/1191374/subprocess-with-timeout

        self._wait4process(timeout)

        # if timeout is not None:
        #     if not self._thread:
        #         self._thread = threading.Thread(target=self._wait4process)
        #         self._thread.daemon = True
        #         self._thread.start()

        # if self._thread:
        #     self._thread.join(timeout=timeout)
        #     self.timeout_happened = self.timeout_happened or self._thread.is_alive()
        # else:
        #     # no timeout and no existing thread
        #     self._wait4process()

        return self

    def _wait4process(self, timeout=None):
        if self._outputs_processed:
            return

        if not self.popen:
            return

        if self.use_temp_files:
            try:
                self.popen.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.timeout_happened = True
                log.debug("timeout")
                return

            self._stdout_file.seek(0)
            self._stderr_file.seek(0)
            self.stdout = self._stdout_file.read()
            self.stderr = self._stderr_file.read()

            self._stdout_file.close()
            self._stderr_file.close()
        else:
            # This will deadlock when using stdout=PIPE and/or stderr=PIPE
            # and the child process generates enough output to a pipe such
            # that it blocks waiting for the OS pipe buffer to accept more data.
            # Use communicate() to avoid that.
            # self.popen.wait()
            # self.stdout = self.popen.stdout.read()
            # self.stderr = self.popen.stderr.read()

            try:
                (self.stdout, self.stderr) = self.popen.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.timeout_happened = True
                log.debug("timeout")
                return
        log.debug("process has ended, return code=%s", self.return_code)
        self.stdout = _rm_ending_lf(unidecode(self.stdout))
        self.stderr = _rm_ending_lf(unidecode(self.stderr))
        self._outputs_processed = True

        #            def limit_str(s):
        #                if len(s) > self.max_bytes_to_log:
        #                    warn = '[middle of output was removed, max_bytes_to_log=%s]'%(self.max_bytes_to_log)
        #                    s = s[:self.max_bytes_to_log / 2] + warn + s[-self.max_bytes_to_log / 2:]
        #                return s
        if self.enable_stdout_log:
            log.debug("stdout=%s", self.stdout)
        if self.enable_stderr_log:
            log.debug("stderr=%s", self.stderr)

    def stop(self) -> "EasyProcess":
        """Kill process and wait for command to complete.

        same as:
         1. :meth:`sendstop`
         2. :meth:`wait`

        :rtype: self

        """
        self.sendstop().wait()
        # if self.is_alive() and kill_after is not None:
        #     self.sendstop(kill=True).wait()
        return self

    def sendstop(self) -> "EasyProcess":
        """
        Kill process (:meth:`subprocess.Popen.terminate`).
        Do not wait for command to complete.

        :rtype: self
        """
        if not self.is_started:
            raise EasyProcessError(self, "process was not started!")

        log.debug('stopping process (pid=%s cmd="%s")', self.pid, self.cmd)
        if self.popen:
            if self.is_alive():
                log.debug("process is active -> calling kill()")
                self.popen.kill()

                # signame = "SIGKILL" if kill else "SIGTERM"
                # log.debug("process is active -> sending " + signame)

                # try:
                #     try:
                #         if kill:
                #             self.popen.kill()
                #         else:
                #             self.popen.terminate()
                #     except AttributeError:
                #         os.kill(self.popen.pid, signal.SIGKILL)
                # except OSError as oserror:
                #     log.debug("exception in terminate:%s", oserror)

            else:
                log.debug("process was already stopped")
        else:
            log.debug("process was not started")

        return self

    def sleep(self, sec: float) -> "EasyProcess":
        """
        sleeping (same as :func:`time.sleep`)

        :rtype: self
        """
        time.sleep(sec)

        return self

    def wrap(self, func, delay=0):
        """
        returns a function which:
         1. start process
         2. call func, save result
         3. stop process
         4. returns result

        similar to :keyword:`with` statement

        :rtype:
        """

        def wrapped():
            self.start()
            if delay:
                self.sleep(delay)
            x = None
            try:
                x = func()
            except OSError as oserror:
                log.debug("OSError exception:%s", oserror)
                self.oserror = oserror
                raise EasyProcessError(self, "wrap error!")
            finally:
                self.stop()
            return x

        return wrapped

    def __enter__(self):
        """used by the :keyword:`with` statement"""
        self.start()
        return self

    def __exit__(self, *exc_info):
        """used by the :keyword:`with` statement"""
        self.stop()
