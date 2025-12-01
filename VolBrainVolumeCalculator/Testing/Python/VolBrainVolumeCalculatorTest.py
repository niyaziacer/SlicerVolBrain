import unittest
import slicer

class VolBrainVolumeCalculatorTest(unittest.TestCase):
    def setUp(self):
        slicer.mrmlScene.Clear()
    
    def test_module_exists(self):
        """Test that module can be loaded"""
        self.assertIsNotNone(slicer.modules.volbrainvolumecalculator)
    
    def test_widget_creation(self):
        """Test widget can be instantiated"""
        from VolBrainVolumeCalculator import VolBrainVolumeCalculatorWidget
        widget = VolBrainVolumeCalculatorWidget()
        self.assertIsNotNone(widget)