
import os
import sys
import time
import yaml
import argparse
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detectors.oom_detector import OOMDetector
from src.detectors.panic_detector import PanicDetector
from src.detectors.reboot_detector import RebootDetector

class ExceptionMonitor:
    def __init__(self, config_path=None):
        self.config = self.load_config(config_path)
        self.detectors = []
        self.results = []
        self.start_time = time.time()
        self.setup_detectors()
        print(f"✅ 已启用 {len(self.detectors)} 个检测器")
    
    def load_config(self, config_path):
        """加载配置文件，提供更健壮的默认配置"""
        default_config = {
            'log_paths': [
                '/var/log/kern.log',
                '/var/log/syslog',
                './test.log'
            ],
            'detectors': {
                'oom': {
                    'enabled': True,
                    'keywords': [
                        'Out of memory',
                        'oom-killer',
                        'Killed process',
                        'Memory cgroup out of memory'
                    ]
                },
                'panic': {
                    'enabled': True,
                    'keywords': [
                        'Kernel panic',
                        'kernel panic',
                        'not syncing',
                        'System halted'
                    ]
                },
                'reboot': {
                    'enabled': True,
                    'keywords': [
                        'unexpectedly shut down',
                        'unexpected restart',
                        'system reboot'
                    ]
                }
            }
        }

        if not config_path or not os.path.exists(config_path):
            print(f"⚠️  警告: 配置文件 {config_path} 不存在，使用默认配置")
            return default_config

        try:
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f) or {}
            
            # 深度合并配置
            config = default_config.copy()
            for key in user_config:
                if key in config and isinstance(config[key], dict):
                    config[key].update(user_config[key])
                else:
                    config[key] = user_config[key]
            
            return config
        except Exception as e:
            print(f"❌ 错误: 无法加载配置文件 {config_path}: {e}")
            return default_config
    
    def setup_detectors(self):
        """初始化检测器，增加调试信息"""
        detector_configs = self.config.get('detectors', {})
        
        if detector_configs.get('oom', {}).get('enabled', False):
            self.detectors.append(OOMDetector(detector_configs['oom']))
            print(f"   - OOM检测器已加载 (关键词: {detector_configs['oom'].get('keywords', [])})")
        
        if detector_configs.get('panic', {}).get('enabled', False):
            self.detectors.append(PanicDetector(detector_configs['panic']))
            print(f"   - Panic检测器已加载 (关键词: {detector_configs['panic'].get('keywords', [])})")
        
        if detector_configs.get('reboot', {}).get('enabled', False):
            self.detectors.append(RebootDetector(detector_configs['reboot']))
            print(f"   - Reboot检测器已加载 (关键词: {detector_configs['reboot'].get('keywords', [])})")
    
    def scan_logs(self):
        """扫描日志文件，增加详细输出"""
        print("\n🔍 开始扫描系统日志...")
        total_files = 0
        total_detections = 0
        
        for log_path in self.config['log_paths']:
            abs_path = os.path.abspath(log_path)
            if not os.path.exists(abs_path):
                print(f"⚠️  跳过不存在的日志文件: {abs_path}")
                continue
            
            print(f"📖 正在读取: {abs_path}")
            detections = self.check_log_file(abs_path)
            total_detections += len(detections)
            total_files += 1
        
        elapsed_time = time.time() - self.start_time
        print(f"\n📊 扫描完成!")
        print(f"   扫描文件数: {total_files}")
        print(f"   总检测次数: {total_detections}")
        print(f"   耗时: {elapsed_time:.2f}秒")
        
        if total_detections > 0:
            self.show_statistics()
        else:
            print("\nℹ️  未检测到任何异常事件")
            print("可能原因:")
            print("1. 日志文件中确实没有匹配的异常")
            print("2. 检测关键词需要调整")
            print("3. 需要检查日志文件权限")
    
    def check_log_file(self, log_path):
        """检查单个日志文件，增加行数统计"""
        detections = []
        line_count = 0
        
        try:
            with open(log_path, 'r', errors='ignore') as f:
                for line in f:
                    line_count += 1
                    result = self.analyze_line(line)
                    if result:
                        result.update({
                            'file': log_path,
                            'line_number': line_count
                        })
                        detections.append(result)
            
            print(f"   共扫描 {line_count} 行日志")
            return detections
        except PermissionError:
            print(f"❌ 权限不足，无法读取: {log_path}")
            print("💡 尝试使用 sudo 运行:")
            print(f"   sudo python3 {__file__}")
            return []
        except Exception as e:
            print(f"❌ 读取日志文件 {log_path} 出错: {e}")
            return []
    
    def analyze_line(self, line):
        """分析单行日志，增加调试输出"""
        for detector in self.detectors:
            result = detector.detect(line)
            if result:
                self.handle_detection(result)
                return result
        return None
    
    def handle_detection(self, result):
        """处理检测结果，优化输出格式"""
        self.results.append(result)
        
        # 根据严重级别选择表情符号
        severity_emoji = {
            'critical': '🔥',
            'high': '🚨',
            'medium': '⚠️',
            'low': 'ℹ️'
        }.get(result.get('severity', 'medium'), '📝')
        
        print(f"{severity_emoji} [{result['type'].upper()}] {result['message'][:100]}...")
    
    def show_statistics(self):
        """显示统计信息，按类型分类"""
        print("\n📈 检测统计:")
        print("-" * 50)
        
        stats = {}
        for detector in self.detectors:
            count = len([r for r in self.results if r['type'] == detector.name])
            if count > 0:
                stats[detector.name] = count
        
        if not stats:
            print("   未检测到任何异常事件")
            return
        
        for name, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {name.upper():<8}: {count} 次")
    
    def save_report(self, output_file):
        """保存检测报告，增加更多详细信息"""
        if not self.results:
            print("⚠️  没有检测到异常，不生成报告")
            return
        
        try:
            with open(output_file, 'w') as f:
                f.write("=" * 60 + "\n")
                f.write("操作系统异常检测报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                for i, result in enumerate(self.results, 1):
                    f.write(f"{i}. [{result['type'].upper()}] {result.get('severity', 'UNKNOWN').upper()}\n")
                    f.write(f"   时间: {result.get('formatted_time', '未知')}\n")
                    f.write(f"   文件: {result.get('file', '未知')}:{result.get('line_number', '未知')}\n")
                    f.write(f"   内容: {result['message']}\n")
                    f.write("-" * 60 + "\n")
            
            print(f"📄 报告已保存至: {os.path.abspath(output_file)}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")

def parse_args():
    """解析命令行参数，增加帮助信息"""
    parser = argparse.ArgumentParser(
        description='操作系统异常信息检测工具',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('-c', '--config',
                       default='config/default.yaml',
                       help='指定配置文件路径')
    
    parser.add_argument('-o', '--output',
                       help='指定输出报告文件路径')
    
    return parser.parse_args()

def main():
    """主程序入口，增加欢迎信息"""
    print("=" * 60)
    print("🖥️  操作系统异常信息检测工具 v1.0")
    print("=" * 60)
    
    args = parse_args()
    monitor = ExceptionMonitor(args.config)
    monitor.scan_logs()
    
    if args.output:
        monitor.save_report(args.output)

if __name__ == "__main__":
    main()
