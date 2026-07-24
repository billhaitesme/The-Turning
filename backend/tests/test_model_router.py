import unittest
from services.model_router import choose_route
from models.routing import TaskType

class Tests(unittest.TestCase):
    def test_vision(self):
        self.assertEqual(choose_route("image", has_image=True).task_type, TaskType.VISION)
    def test_current(self):
        route = choose_route("latest AI news")
        self.assertEqual(route.task_type, TaskType.GENERAL)
        self.assertEqual(route.reason, "User Selection")
    def test_technical(self):
        self.assertEqual(
            choose_route("Explain FastAPI").model,
            choose_route("Discuss philosophy").model,
        )

if __name__ == "__main__":
    unittest.main()
