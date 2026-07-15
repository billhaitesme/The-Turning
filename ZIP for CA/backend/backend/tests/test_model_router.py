import unittest
from services.model_router import choose_route
from models.routing import TaskType

class Tests(unittest.TestCase):
    def test_vision(self):
        self.assertEqual(choose_route("image", has_image=True).task_type, TaskType.VISION)
    def test_current(self):
        self.assertEqual(choose_route("latest AI news").task_type, TaskType.CURRENT_INFO)
    def test_technical(self):
        self.assertEqual(choose_route("Explain FastAPI").task_type, TaskType.TECHNICAL)

if __name__ == "__main__":
    unittest.main()
