import unittest

import auto_video


class AutoVideoHelperTests(unittest.TestCase):
    def test_double_speed_text_accepts_common_videojs_labels(self):
        self.assertTrue(auto_video.is_double_speed_text("2x"))
        self.assertTrue(auto_video.is_double_speed_text("2X"))
        self.assertTrue(auto_video.is_double_speed_text("2.0x"))
        self.assertTrue(auto_video.is_double_speed_text("2.0 倍"))
        self.assertFalse(auto_video.is_double_speed_text("1.5x"))
        self.assertFalse(auto_video.is_double_speed_text(""))

    def test_video_complete_message_includes_label(self):
        self.assertEqual(
            auto_video.video_complete_message("第一讲"),
            "已完成第一讲视频播放",
        )
        self.assertEqual(
            auto_video.video_complete_message(None),
            "已完成视频播放",
        )


if __name__ == "__main__":
    unittest.main()
