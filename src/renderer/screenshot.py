"""Selenium 截图模块"""
import datetime as dt
import io
import time
from pathlib import Path
from typing import Optional

import config

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ScreenshotRenderer:
    """使用 Selenium + Chrome 进行网页截图"""

    def __init__(
        self,
        width: int = 390,
        device_scale_factor: int = 2,
        headless: bool = True
    ):
        """
        初始化截图渲染器

        Args:
            width: 视口宽度（CSS 像素）
            device_scale_factor: 设备像素比（2 = 2x 高清）
            headless: 是否无头模式
        """
        self.width = width
        self.device_scale_factor = device_scale_factor
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """初始化 Chrome WebDriver"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
        except ImportError:
            raise ImportError(
                "需要安装 selenium：pip install selenium\n"
                "还需要安装 Chrome 和 ChromeDriver"
            )

        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        # 基础设置
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--window-size={self.width},800")

        # 禁用不必要的功能
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")

        # 设置语言
        options.add_argument("--lang=zh-CN")

        try:
            # 尝试使用 webdriver-manager 自动管理 ChromeDriver
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except ImportError:
            # 如果没有 webdriver-manager，尝试直接使用系统 ChromeDriver
            self.driver = webdriver.Chrome(options=options)

        # 设置设备像素比（用于高清截图）
        self.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": self.width,
            "height": 800,
            "deviceScaleFactor": self.device_scale_factor,
            "mobile": True
        })

    def capture(self, url: str, output_path: Optional[Path] = None,
                format: str = "jpg", quality: int = 35) -> Path:
        """
        截取网页截图

        Args:
            url: 网页 URL
            output_path: 输出文件路径（可选）
            format: 输出格式，"jpg" 或 "png"
            quality: JPG 质量（1-100），仅对 JPG 有效

        Returns:
            截图文件路径
        """
        if self.driver is None:
            self._init_driver()

        # 加载页面
        self.driver.get(url)

        # 等待页面加载完成
        time.sleep(1)

        # 获取页面实际高度
        total_height = self.driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
        )

        # 更新视口高度以包含整个页面
        self.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": self.width,
            "height": total_height,
            "deviceScaleFactor": self.device_scale_factor,
            "mobile": True
        })

        # 再次等待，确保渲染完成
        time.sleep(0.5)

        # 生成输出路径
        ext = "jpg" if format.lower() in ("jpg", "jpeg") else "png"
        if output_path is None:
            timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
            output_path = config.SCREENSHOTS_DIR / f"quick_{timestamp}.{ext}"

        output_path = Path(output_path)

        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 截图
        if ext == "jpg" and HAS_PIL:
            # 先截取 PNG 到内存，再转换为 JPG
            png_data = self.driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(png_data))
            # 转换为 RGB（JPG 不支持透明通道）
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (0, 0, 0))  # 黑色背景配合深色主题
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(str(output_path), 'JPEG', quality=quality, optimize=True)
        else:
            # 直接保存 PNG
            self.driver.save_screenshot(str(output_path))

        return output_path

    def capture_from_file(self, html_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        从本地 HTML 文件截图

        Args:
            html_path: HTML 文件路径
            output_path: 输出文件路径（可选）

        Returns:
            截图文件路径
        """
        file_url = f"file://{html_path.resolve()}"
        return self.capture(file_url, output_path)

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def capture_quick_digest(
    page_url: str,
    output_path: Optional[Path] = None,
    width: int = 390,
    device_scale_factor: int = 2
) -> Path:
    """
    便捷函数：截取快讯页面

    Args:
        page_url: 页面 URL
        output_path: 输出路径（可选）
        width: 视口宽度
        device_scale_factor: 设备像素比

    Returns:
        截图文件路径
    """
    with ScreenshotRenderer(width=width, device_scale_factor=device_scale_factor) as renderer:
        return renderer.capture(page_url, output_path)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="网页截图工具")
    parser.add_argument("url", help="要截图的 URL")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-w", "--width", type=int, default=390, help="视口宽度")
    parser.add_argument("-s", "--scale", type=int, default=2, help="设备像素比")
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else None

    with ScreenshotRenderer(width=args.width, device_scale_factor=args.scale) as renderer:
        result = renderer.capture(args.url, output_path)
        print(f"截图已保存到：{result}")


if __name__ == "__main__":
    main()
