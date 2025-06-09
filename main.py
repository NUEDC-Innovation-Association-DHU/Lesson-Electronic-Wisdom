import utime
import time
from machine import Pin, PWM
from neopixel import NeoPixel


# 音乐播放一遍（30s轻音乐）
import wav
wav.yinyue()


# 设置IO18为PWM输出，频率10kHz，占空比50%
pwm1 = PWM(Pin(18))  # 创建PWM对象
pwm1.freq(1000)     # 设置频率为10kHz
pwm1.duty(0)       # 设置占空比为50%（ESP32上范围是0-1023，所以50%是512）
pwm2 = PWM(Pin(5))  # 创建PWM对象
pwm2.freq(1000)     # 设置频率为10kHz
pwm2.duty(0)       # 设置占空比为50%（ESP32上范围是0-1023，所以50%是512）

utime.sleep(2)
# 设置IO17为输出模式，并输出高电平
dire1 = Pin(17, Pin.OUT)
dire1.value(1)  # 设置为高电平
dire2 = Pin(16, Pin.OUT)
dire2.value(1)  # 设置为高电平

# 设置IO18为PWM输出，频率10kHz，占空比50%
pwm1.duty(300)       # 设置占空比为50%（ESP32上范围是0-1023，所以50%是512）
pwm2.duty(300)       # 设置占空比为50%（ESP32上范围是0-1023，所以50%是512）

print("PWM在IO18上运行，占空比50%")
print("IO17输出高电平")

# Initialize pin and strip
pin = Pin(32, Pin.OUT)
np = NeoPixel(pin, 1)  # Single LED

# Define rainbow colors (Red, Orange, Yellow, Green, Cyan, Blue, Purple)
rainbow_colors = [
    (255, 0, 0),      # Red
    (255, 165, 0),    # Orange
    (255, 255, 0),    # Yellow
    (0, 255, 0),      # Green
    (0, 255, 255),    # Cyan
    (0, 0, 255),      # Blue
    (128, 0, 128)     # Purple
]

# Function to gradually transition between colors
def fade(old_color, new_color, transition_time=1.0):
    steps = 50  # Number of steps in the transition
    delay = transition_time / steps
    
    r_old, g_old, b_old = old_color
    r_new, g_new, b_new = new_color
    
    r_step = (r_new - r_old) / steps
    g_step = (g_new - g_old) / steps
    b_step = (b_new - b_old) / steps
    
    for i in range(steps):
        r = int(r_old + r_step * i)
        g = int(g_old + g_step * i)
        b = int(b_old + b_step * i)
        
        # Keep values in valid range
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        np[0] = (r, g, b)
        np.write()
        utime.sleep(delay)
    
    # Make sure we end exactly at the target color
    np[0] = new_color
    np.write()

# Main loop
current_color = (0, 0, 0)  # Start with black
color_index = 0

while True:
    # Get the next color
    next_color = rainbow_colors[color_index]
    
    # Fade to the next color over 1 second
    fade(current_color, next_color)
    
    # Display the color for 2 seconds
    utime.sleep(2)
    
    # Update the current color
    current_color = next_color
    
    # Move to the next color in the cycle
    color_index = (color_index + 1) % len(rainbow_colors)


