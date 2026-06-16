# hardware/hardware_interface.py
from __future__ import annotations

import json
import serial
import threading
import queue
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class HardwareEvent:
    """硬件事件"""
    event_type: str  # "nfc_scan", "scale_weight", "button_press"
    data: Dict
    timestamp: str


class HardwareInterface:
    """
    硬件连接接口
    支持：ESP8266/ESP32 (串口/WiFi)、NFC、Arduino
    """

    def __init__(self, port: str = "COM3", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn: Optional[serial.Serial] = None
        self.is_connected = False
        self.event_queue: queue.Queue = queue.Queue()
        self.event_handlers: List[Callable] = []
        self._running = False

    def connect(self) -> bool:
        """连接硬件"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            self.is_connected = True
            self._running = True
            # 启动监听线程
            threading.Thread(target=self._listen, daemon=True).start()
            print(f"✅ 硬件已连接: {self.port}")
            return True
        except Exception as e:
            print(f"❌ 硬件连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self._running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.is_connected = False
        print("🔌 硬件已断开")

    def _listen(self):
        """监听串口数据"""
        while self._running and self.serial_conn:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line:
                        self._parse_message(line)
            except Exception as e:
                print(f"串口监听错误: {e}")
                break

    def _parse_message(self, message: str):
        """解析硬件消息"""
        try:
            # 尝试解析JSON
            data = json.loads(message)
            event_type = data.get("type", "unknown")
            event = HardwareEvent(
                event_type=event_type,
                data=data.get("data", {}),
                timestamp=datetime.now().isoformat()
            )
            self.event_queue.put(event)
            self._notify_handlers(event)
        except json.JSONDecodeError:
            # 非JSON格式，尝试解析简单命令
            if message.startswith("NFC:"):
                uid = message[4:].strip()
                self.event_queue.put(HardwareEvent(
                    event_type="nfc_scan",
                    data={"uid": uid},
                    timestamp=datetime.now().isoformat()
                ))
            elif message.startswith("WEIGHT:"):
                weight = float(message[7:].strip())
                self.event_queue.put(HardwareEvent(
                    event_type="scale_weight",
                    data={"weight": weight},
                    timestamp=datetime.now().isoformat()
                ))

    def _notify_handlers(self, event: HardwareEvent):
        """通知所有事件处理器"""
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"事件处理器错误: {e}")

    def on_event(self, handler: Callable):
        """注册事件处理器"""
        self.event_handlers.append(handler)

    def send_command(self, command: str, data: Optional[Dict] = None) -> bool:
        """发送命令到硬件"""
        if not self.is_connected or not self.serial_conn:
            return False

        try:
            msg = json.dumps({"command": command, "data": data or {}})
            self.serial_conn.write((msg + "\n").encode('utf-8'))
            return True
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False

    def scan_nfc(self) -> Optional[str]:
        """扫描NFC标签（同步等待）"""
        if not self.is_connected:
            return None

        self.send_command("scan_nfc")
        # 等待事件
        try:
            event = self.event_queue.get(timeout=5)
            if event.event_type == "nfc_scan":
                return event.data.get("uid")
        except queue.Empty:
            pass
        return None

    def get_event(self, timeout: float = 1.0) -> Optional[HardwareEvent]:
        """获取下一个硬件事件"""
        try:
            return self.event_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_status(self) -> Dict:
        """获取硬件状态"""
        return {
            "connected": self.is_connected,
            "port": self.port,
            "baudrate": self.baudrate,
            "queue_size": self.event_queue.qsize()
        }