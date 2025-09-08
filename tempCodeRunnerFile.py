import unittest
from data.nuevos import build_pwl_arc

class TestBuildPWLArc(unittest.TestCase):
    def test_basic_usage(self):
  
        x = [0, 1, 2, 3]
        y = [0, 2, 4, 6]
        
        result = build_pwl_arc.build_pwl(x, y)
 
        expected = [(0, 0), (1, 2), (2, 4), (3, 6)]
        self.assertEqual(result, expected)

    def test_empty_input(self):
        x = []
        y = []
        result = build_pwl_arc.build_pwl(x, y)
        expected = []
        self.assertEqual(result, expected)

    def test_invalid_input_length(self):
        x = [0, 1]
        y = [0]
        with self.assertRaises(Exception):
            build_pwl_arc.build_pwl(x, y)

if __name__ == '__main__':
    unittest.main()