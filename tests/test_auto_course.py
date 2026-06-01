import unittest

import auto_course


class AutoCourseHelperTests(unittest.TestCase):
    def test_completed_text_requires_exact_completed_status(self):
        self.assertTrue(auto_course.is_completed_status("已完成"))
        self.assertTrue(auto_course.is_completed_status("  已完成\n"))
        self.assertFalse(auto_course.is_completed_status("未完成"))
        self.assertFalse(auto_course.is_completed_status(""))

    def test_task_icon_completion_uses_aria_label(self):
        self.assertTrue(auto_course.is_completed_task_icon("任务点已完成"))
        self.assertTrue(auto_course.is_completed_task_icon(" 视频任务点已完成 "))
        self.assertFalse(auto_course.is_completed_task_icon("任务点未完成"))
        self.assertFalse(auto_course.is_completed_task_icon(None))


if __name__ == "__main__":
    unittest.main()
