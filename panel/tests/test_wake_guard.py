import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("wake_guard", Path(__file__).parents[1] / "ha-panel-wake-guard.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WakeGuardTests(unittest.TestCase):
    def test_holding_a_touch_never_reveals_the_dashboard(self):
        gate = module.WakeGate()
        gate.press("touch", 1.0)
        self.assertFalse(gate.can_reveal(100.0))

    def test_release_is_consumed_before_dashboard_is_revealed(self):
        gate = module.WakeGate()
        gate.press("touch", 1.0)
        gate.release("touch", 2.0)
        self.assertFalse(gate.can_reveal(2.2))
        self.assertTrue(gate.can_reveal(2.4))

    def test_trailing_mouse_event_extends_the_guard(self):
        gate = module.WakeGate()
        gate.press("touch", 1.0)
        gate.release("touch", 1.2)
        gate.press(("button", 1), 1.3)
        self.assertFalse(gate.can_reveal(2.0))
        gate.release(("button", 1), 2.0)
        self.assertFalse(gate.can_reveal(2.2))
        self.assertTrue(gate.can_reveal(2.4))

    def test_multiple_input_devices_must_all_be_released(self):
        gate = module.WakeGate()
        gate.press("touch", 1.0)
        gate.press(("key", 20), 1.1)
        gate.release("touch", 1.2)
        self.assertFalse(gate.can_reveal(10.0))
        gate.release(("key", 20), 10.0)
        self.assertTrue(gate.can_reveal(10.4))

    def test_resume_without_a_delivered_touch_still_reveals(self):
        gate = module.WakeGate()
        self.assertFalse(gate.can_reveal(1.0))
        gate.wake(1.0)
        self.assertTrue(gate.can_reveal(2.0))


if __name__ == "__main__":
    unittest.main()
