import asyncio
import threading
import time

import gpiod


class D5Button:
    """
    Watches Raspberry Pi GPIO D5 (GPIO 5).

    Wiring:
      D5 -> GPIO 5
      GND -> GND

    The button uses the Pi's internal pull-up, so:
      released = HIGH
      pressed  = LOW

    Logical sequence:
      press -> release = START
      next press       = STOP
    """

    CHIP = "/dev/gpiochip0"
    LINE = 5

    def __init__(self):
        self._request = None
        self._thread = None
        self._stop_event = threading.Event()
        self._listeners = []

    def add_listener(self, callback):
        self._listeners.append(callback)

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="d5-button",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

        if self._request is not None:
            self._request.release()
            self._request = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

        self._thread = None

    def _emit(self, event):
        for callback in list(self._listeners):
            try:
                callback(event)
            except Exception as exc:
                print(f"D5 listener error: {exc}")

    def _run(self):
        request = gpiod.request_lines(
            self.CHIP,
            consumer="language-pet-d5",
            config={
                self.LINE: gpiod.LineSettings(
                    direction=gpiod.line.Direction.INPUT,
                    bias=gpiod.line.Bias.PULL_UP,
                )
            },
        )

        self._request = request

        try:
            recording = False

            while not self._stop_event.is_set():
                value = request.get_value(self.LINE)

                if value == gpiod.line.Value.INACTIVE:
                    # Button is pressed.
                    if not recording:
                        # First press: wait for release before starting.
                        while (
                            request.get_value(self.LINE)
                            == gpiod.line.Value.INACTIVE
                            and not self._stop_event.is_set()
                        ):
                            time.sleep(0.01)

                        if not self._stop_event.is_set():
                            recording = True
                            print("D5: START")
                            self._emit("start")
                    else:
                        # Second press: stop immediately.
                        recording = False
                        print("D5: STOP")
                        self._emit("stop")

                        # Wait for release before looking for another press.
                        while (
                            request.get_value(self.LINE)
                            == gpiod.line.Value.INACTIVE
                            and not self._stop_event.is_set()
                        ):
                            time.sleep(0.01)

                time.sleep(0.01)

        finally:
            if self._request is request:
                self._request = None

            request.release()


button = D5Button()
