from datetime import datetime

def log(message):
    """
    打印带有时间戳的日志
    格式: 【YYYY-MM-DD HH:mm:ss.SSS  message】
    """
    now = datetime.now()
    # 格式化为 YYYY-MM-DD HH:mm:ss.SSS
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    # strftime %f is microseconds (000000), we need milliseconds (000)
    millis = now.strftime("%f")[:3]
    
    print(f"【{time_str}.{millis}  {message}】")
