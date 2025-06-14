import utime
import time
from machine import Pin, PWM, ADC, UART
from neopixel import NeoPixel
import _thread
import gc
# import wav
from sr04 import HCSR04

# 全局变量
running = True
val_4 = 0
val_0 = 0
adc_lock = _thread.allocate_lock()  # 使用更安全的锁
uart_queue = []  # UART发送队列
uart_lock = _thread.allocate_lock()  # UART队列锁
MAX_QUEUE_SIZE = 10  # 限制队列最大长度

uart2 = UART(2, baudrate=9600, tx=Pin(14), rx=Pin(27))

def uart_send_nextion(cmd):
    """将命令添加到发送队列"""
    with uart_lock:
        if len(uart_queue) < MAX_QUEUE_SIZE:  # 防止队列过长
            uart_queue.append(cmd)

def uart_thread():
    """UART发送线程"""
    try:
        while running:
            cmd = None
            with uart_lock:
                if uart_queue:
                    cmd = uart_queue.pop(0)  # 取出第一个命令
            
            if cmd:
                try:
                    if isinstance(cmd, str):
                        uart2.write(cmd.encode('ascii'))
                        uart2.write(b'\xff\xff\xff')
                    elif isinstance(cmd, bytes):
                        uart2.write(cmd)
                    utime.sleep(0.01)
                except Exception as e:
                    print(f"UART发送错误: {e}")
                finally:
                    del cmd  # 手动删除引用
                    gc.collect()  # 强制垃圾回收
            
            utime.sleep(0.05)  # 增加间隔，减少CPU占用
    except Exception as e:
        print(f"UART线程错误: {e}")

def ultrasound_thread():
    global distance_cm
    
    try:
        hcsr04=HCSR04(trigger_pin=23,echo_pin=22)      
        while running:
            distance_cm = hcsr04.distance_cm()
            utime.sleep(0.1)
            gc.collect()  # 定期回收内存
    except Exception as e:
        print(f"超声波线程错误: {e}")

def adc_thread():
    global val_4, val_0
    try:
        # 初始化ADC引脚
        adc_4 = ADC(Pin(4))
        adc_0 = ADC(Pin(12))
        adc_4.atten(ADC.ATTN_11DB)
        adc_0.atten(ADC.ATTN_11DB)

        while running:
            temp_val_4 = adc_4.read()
            temp_val_0 = adc_0.read()
            
            with adc_lock:  # 使用with语句更安全
                val_4 = temp_val_4
                val_0 = temp_val_0
            
            utime.sleep(0.01)  # 增加间隔
    except Exception as e:
        print(f"ADC线程错误: {e}")

def rgb_thread():
    np = None
    try:
        pin = Pin(32, Pin.OUT)
        np = NeoPixel(pin, 1)
        
        rainbow_colors = [
            (255, 0, 0), (255, 165, 0), (255, 255, 0),
            (0, 255, 0), (0, 255, 255), (0, 0, 255), (128, 0, 128)
        ]
        
        def fade(old_color, new_color, transition_time=1.0):
            steps = 20  # 减少步数，节省内存
            delay = transition_time / steps
            
            r_old, g_old, b_old = old_color
            r_new, g_new, b_new = new_color
            
            r_step = (r_new - r_old) / steps
            g_step = (g_new - g_old) / steps
            b_step = (b_new - b_old) / steps
            
            for i in range(steps):
                if not running:
                    break
                r = max(0, min(255, int(r_old + r_step * i)))
                g = max(0, min(255, int(g_old + g_step * i)))
                b = max(0, min(255, int(b_old + b_step * i)))
                
                np[0] = (r, g, b)
                np.write()
                utime.sleep(delay)
            
            np[0] = new_color
            np.write()
        
        current_color = (0, 0, 0)
        color_index = 0
        while running:
            next_color = rainbow_colors[color_index]
            fade(current_color, next_color)
            
            if not running:
                break
                
            utime.sleep(2)
            current_color = next_color
            color_index = (color_index + 1) % len(rainbow_colors)
            gc.collect()  # 每次循环后回收内存
            
    except Exception as e:
        print(f"RGB线程错误: {e}")
    finally:
        if np is not None:
            try:
                np[0] = (0, 0, 0)
                np.write()
            except:
                pass

def control_thread():
    global val_4, val_0
    pwm1 = None
    pwm2 = None
    send_counter = 0  # 发送计数器，减少发送频率
    
    try:
        utime.sleep(2)
        
        kp = 0.1
        speed1 = 512.0
        speed2 = 512.0
        
        pwm2 = PWM(Pin(17))
        pwm2.freq(1000)
        pwm2.duty(0)
        
        pwm1 = PWM(Pin(16))
        pwm1.freq(1000)
        pwm1.duty(0)
        
        dire2 = Pin(18, Pin.OUT)
        dire2.value(1)
        dire1 = Pin(5, Pin.OUT)
        dire1.value(1)
        
        pwm1.duty(int(speed1))
        pwm2.duty(int(speed2))
        
        while running:
            with adc_lock:
                local_val_4 = val_4
                local_val_0 = val_0
            
            error = local_val_4 - local_val_0
            
            print("ADC4: {}, ADC0: {}, error:{}".format(local_val_4, local_val_0, error))
            
            # 每10次循环才发送一次UART，减少内存压力
            send_counter += 1
            if send_counter >= 100:
                # 预格式化字符串，避免重复创建
                msg = "ADC4:{}".format(local_val_4)
                uart_cmd = 'page0.t2.txt="{}"'.format(msg)
                uart_send_nextion(uart_cmd)
                
                msg = "ADC0:{}".format(local_val_0)
                uart_cmd = 'page0.t3.txt="{}"'.format(msg)
                uart_send_nextion(uart_cmd)
   
                msg = "err:{}".format(error)
                uart_cmd = 'page0.t4.txt="{}"'.format(msg)
                uart_send_nextion(uart_cmd)
                send_counter = 0
                del msg, uart_cmd  # 手动删除引用
            
            # PID控制
            new_speed1 = speed1 - error * kp
            new_speed2 = speed2 + error * kp
            
            if 255 <= new_speed1 <= 767:
                speed1 = new_speed1
            if 255 <= new_speed2 <= 767:
                speed2 = new_speed2
            
            pwm1.duty(int(speed1))
            pwm2.duty(int(speed2))
            
            if not running:
                break
            utime.sleep(0.01)  # 增加间隔，减少循环频率
            
            # 定期回收内存
            if send_counter % 5 == 0:
                gc.collect()
            
    except Exception as e:
        print(f"控制线程错误: {e}")
    finally:
        if pwm1 is not None:
            try:
                pwm1.duty(0)
                pwm1.deinit()
            except:
                pass
        if pwm2 is not None:
            try:
                pwm2.duty(0)
                pwm2.deinit()
            except:
                pass

def main():
    global running
    running = True
    try:
        _thread.start_new_thread(uart_thread, ())
        _thread.start_new_thread(rgb_thread, ())
        _thread.start_new_thread(adc_thread, ())
        _thread.start_new_thread(ultrasound_thread, ())
        _thread.start_new_thread(control_thread, ())
        
        uart_send_nextion('page0.t4.txt="hello"')
        
        while running:
            utime.sleep(1)
            gc.collect()  # 主线程定期回收内存
            
    except KeyboardInterrupt:
        running = False
    except Exception as e:
        running = False
    finally:
        running = False
        utime.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        running = False
    finally:
        print("程序结束")
