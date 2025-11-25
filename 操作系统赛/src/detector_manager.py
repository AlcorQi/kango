import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detectors.oom_detector import OOMDetector
from src.detectors.panic_detector import PanicDetector
from src.detectors.reboot_detector import RebootDetector
from src.detectors.oops_detector import OopsDetector
from src.detectors.deadlock_detector import DeadlockDetector
from src.detectors.fs_exception_detector import FSExceptionDetector

class DetectorManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.detectors = []
        self.setup_detectors()
    
    def setup_detectors(self):
        """初始化检测器"""
        detector_classes = {
            'oom': OOMDetector,
            'panic': PanicDetector,
            'reboot': RebootDetector,
            'oops': OopsDetector,
            'deadlock': DeadlockDetector,
            'fs_exception': FSExceptionDetector
        }
        
        print("🔧 正在初始化检测器...")
        
        for detector_name, detector_class in detector_classes.items():
            config = self.config_manager.get_detector_config(detector_name)
            if config.get('enabled', False):
                try:
                    detector = detector_class(config)
                    self.detectors.append(detector)
                    keyword_count = len(config.get('keywords', []))
                    print(f"   ✅ {detector_name.upper()}检测器已加载 ({keyword_count}个关键词)")
                except Exception as e:
                    print(f"   ❌ {detector_name.upper()}检测器加载失败: {e}")
            else:
                print(f"   ⚠️  {detector_name.upper()}检测器已禁用")
    
    def analyze_line(self, line):
        """分析单行日志"""
        for detector in self.detectors:
            try:
                result = detector.detect(line)
                if result:
                    return result
            except Exception as e:
                print(f"❌ 检测器 {detector.name} 处理行时出错: {e}")
                print(f"   问题行: {line[:100]}...")
                continue
        return None
    
    def get_detector_names(self):
        """获取所有检测器名称"""
        return [detector.name for detector in self.detectors]