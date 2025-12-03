# llm_analyzer.py
import json
import os
from openai import OpenAI

class LLMAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            api_key="sk-1d620b7df9ea4c36b88b06598b3ad19d",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.model_name = "qwen-plus"
        # 定义六种异常类型
        self.anomaly_types = ['oom', 'panic', 'reboot', 'oops', 'deadlock', 'fs_exception']
    
    def load_anomalies_data(self, data_dir='./data/'):
        """加载异常数据"""
        anomalies_file = os.path.join(data_dir, 'anomalies.ndjson')
        summary_file = os.path.join(data_dir, 'summary.json')
        
        anomalies = []
        summary = {}
        
        # 读取异常记录
        if os.path.exists(anomalies_file):
            with open(anomalies_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        anomalies.append(json.loads(line.strip()))
        
        # 读取摘要信息
        if os.path.exists(summary_file):
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
        
        return anomalies, summary
    
    def get_top_anomalies_by_type(self, anomalies, top_n=3):
        """获取每种异常类型的前top_n条记录"""
        anomalies_by_type = {atype: [] for atype in self.anomaly_types}
        
        # 按类型分组
        for anomaly in anomalies:
            anomaly_type = anomaly.get('type', 'unknown')
            if anomaly_type in anomalies_by_type:
                anomalies_by_type[anomaly_type].append(anomaly)
        
        # 每种类型取前top_n条
        result = {}
        for atype in self.anomaly_types:
            result[atype] = anomalies_by_type[atype][:top_n]
        
        return result
    
    def generate_analysis_prompt(self, anomalies, summary):
        """生成分析提示词"""
        # 获取每种异常类型的前三条记录
        top_anomalies = self.get_top_anomalies_by_type(anomalies, 3)
        
        # 统计异常类型
        anomaly_stats = {}
        for anomaly in anomalies:
            anomaly_type = anomaly.get('type', 'unknown')
            severity = anomaly.get('severity', 'unknown')
            if anomaly_type not in anomaly_stats:
                anomaly_stats[anomaly_type] = {'total': 0, 'severities': {}}
            anomaly_stats[anomaly_type]['total'] += 1
            anomaly_stats[anomaly_type]['severities'][severity] = \
                anomaly_stats[anomaly_type]['severities'].get(severity, 0) + 1
        
        # 构建统计信息字符串
        stats_str = "异常统计信息:\n"
        for anomaly_type in self.anomaly_types:
            if anomaly_type in anomaly_stats:
                stats_str += f"- {anomaly_type.upper()}: {anomaly_stats[anomaly_type]['total']} 次\n"
        
        # 构建每种异常的前三条记录
        details_str = "每种异常类型的前三条记录:\n\n"
        for atype in self.anomaly_types:
            if top_anomalies[atype]:
                details_str += f"{atype.upper()} 异常 (共 {len(top_anomalies[atype])} 条):\n"
                for i, anomaly in enumerate(top_anomalies[atype], 1):
                    details_str += f"{i}. 严重性: {anomaly.get('severity', 'unknown')}, "
                    details_str += f"时间: {anomaly.get('detected_at', '未知')}\n"
                    details_str += f"   信息: {anomaly.get('message', '')}\n"
                details_str += "\n"
        
        prompt = f"""
您是一名专业的系统运维专家，请基于以下操作系统异常检测数据进行分析：

{stats_str}

{details_str}

请按照以下两个部分生成专业分析报告：

第一部分：总结分析模块
请用一段或几段话分析当前系统异常情况和整体现状。要求：
1. 字数控制在200字左右
2. 不要使用任何小标题或小括号
3. 语言清晰、专业、有逻辑
4. 涵盖异常说明和系统现状总结

第二部分：优化建议模块
请以要点形式给出最急需处理的异常或可能隐患的解决方案。要求：
1. 每条建议简短精炼
2. 不少于3条，不多于10条
3. 每条建议以"• "开头
4. 针对最紧急或最重要的问题

请严格按照以下格式返回结果：

【总结分析】
[这里填写您的总结分析内容]

【优化建议】
• 第一条建议
• 第二条建议
• 第三条建议
[继续添加更多建议...]

确保语言面向技术管理人员，专业且实用。
"""
        return prompt
    
    def analyze_system_anomalies(self, data_dir='./data'):
        """分析系统异常并生成报告"""
        try:
            # 加载数据
            anomalies, summary = self.load_anomalies_data(data_dir)
            
            if not anomalies:
                return "未发现异常数据，系统运行正常。"
            
            # 生成提示词
            prompt = self.generate_analysis_prompt(anomalies, summary)
            
            # 调用大模型
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一名专业的系统运维专家，擅长分析操作系统异常和提供优化建议。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3  # 降低随机性，保证专业性和一致性
            )
            
            result = response.choices[0].message.content.strip()
            return result
            
        except Exception as e:
            return f"分析过程中出现错误: {str(e)}"
    
    def save_analysis_report(self, output_file, analysis_result):
        """保存分析报告"""
        try:
            directory = os.path.dirname(os.path.abspath(output_file))
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("操作系统异常智能分析报告\n")
                f.write("基于大语言模型的专业分析\n")
                f.write("=" * 60 + "\n\n")
                
                # 解析结果，确保格式正确
                if "【总结分析】" in analysis_result and "【优化建议】" in analysis_result:
                    f.write(analysis_result)
                else:
                    # 如果格式不正确，直接写入
                    f.write("【总结分析】\n")
                    f.write("系统检测到多种异常类型，需要关注系统稳定性。建议根据以下优化建议进行改进。\n\n")
                    f.write("【优化建议】\n")
                    f.write("• 检查系统日志，确认异常具体原因\n")
                    f.write("• 监控系统资源使用情况，避免资源耗尽\n")
                    f.write("• 定期更新系统补丁和安全更新\n")
                    f.write("\n原始分析结果:\n" + analysis_result)
            
            print(f"📊 LLM分析报告已保存至: {os.path.abspath(output_file)}")
            return True
            
        except Exception as e:
            print(f"❌ 保存LLM分析报告失败: {e}")
            return False