import xml.etree.ElementTree as ET
import json
import os
from feishu import feishu
import urllib3


class RssMonitor:
    """
    一个监控 RSS 订阅源并提取新内容的类。
    """

    def __init__(self, local_storage_path: str):
        """
        初始化 RssMonitor。

        参数:
            local_storage_path (str): 用于存储 RSS 数据的本地目录路径。
                                      数据将保存在此目录下的 'rss_feed_data.json' 文件中。
        """
        self.storage_path = local_storage_path
        # 确保存储目录存在
        os.makedirs(self.storage_path, exist_ok=True)
        self.data_file_path = os.path.join(self.storage_path, "rss_feed_data.json")
        print(
            f"RssMonitor 初始化完毕。数据将存储在: {os.path.abspath(self.data_file_path)}"
        )

    def _fetch_and_parse_rss(self, rss_url: str) -> list[dict]:
        """
        从给定的 URL 获取 RSS 订阅内容并解析。

        参数:
            rss_url (str): RSS 订阅源的 URL。

        返回:
            list[dict]: 包含条目信息的字典列表，每个字典包含 'title', 'link', 和 'guid'。
                        如果获取或解析失败，则返回空列表。
        """
        items = []
        try:
            import requests
            import time
            import warnings

            # 忽略SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # 创建会话保持连接状态
            session = requests.Session()
            session.verify = False

            # 设置类似真实浏览器的headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
                "Referer": "https://linux.do/",
            }

            # 先访问主站获取cookies
            session.get("https://linux.do/", headers=headers, timeout=15)

            # 添加短暂延迟，模拟人类行为
            time.sleep(2)

            # 请求RSS链接
            response = session.get(rss_url, headers=headers, timeout=15)

            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                return []

            content_str = response.text

            if not content_str.strip():
                print("获取到的RSS内容为空")
                return []

            # 检查内容是否为XML
            if not content_str.startswith("<?xml"):
                print(f"获取到的内容可能不是有效的XML: {content_str[:100]}...")
                # 尝试查找XML开始位置
                xml_start = content_str.find("<?xml")
                if xml_start > 0:
                    content_str = content_str[xml_start:]
                else:
                    print("未能找到XML内容，可能是遇到了人机验证")
                    print("正在尝试解决...")
                    # 尝试解析HTML查找保护模式的提示
                    if "just a moment" in content_str.lower():
                        print("检测到Cloudflare保护或类似保护机制")
                    return []

            # 解析XML
            try:
                root = ET.fromstring(content_str)

                # 优先查找 RSS 2.0 标准的 channel/item
                item_elements = root.findall(".//channel/item")
                # 如果找不到，尝试 Atom feed 的 entry
                if not item_elements:
                    item_elements = root.findall("{http://www.w3.org/2005/Atom}entry")

                print(f"找到 {len(item_elements)} 个item元素")

                for item_element in item_elements:
                    title_element = item_element.find("title")
                    title = (
                        title_element.text.strip()
                        if title_element is not None and title_element.text
                        else "N/A"
                    )

                    link_element = item_element.find("link")
                    link = None
                    if link_element is not None:
                        if "href" in link_element.attrib:  # Atom feeds
                            link = link_element.get("href")
                        elif link_element.text:  # RSS
                            link = link_element.text

                    guid_element = item_element.find("guid")  # RSS
                    id_element = item_element.find(
                        "{http://www.w3.org/2005/Atom}id"
                    )  # Atom

                    guid = None
                    if guid_element is not None and guid_element.text:
                        guid = guid_element.text.strip()
                    elif id_element is not None and id_element.text:
                        guid = id_element.text.strip()

                    # 如果 guid 不存在，使用 link 作为唯一标识符
                    if not guid and link:
                        guid = link.strip()

                    if title and link and guid:
                        items.append(
                            {"title": title, "link": link.strip(), "guid": guid}
                        )
                    elif title and guid and not link:
                        items.append({"title": title, "link": "N/A", "guid": guid})

            except ET.ParseError as e:
                print(f"解析 XML 失败: {e}")
                print(f"内容片段: {content_str[:200]}")

        except requests.exceptions.RequestException as e:
            print(f"请求异常 ({rss_url}): {e}")
        except Exception as e:
            print(f"处理 RSS 时发生未知错误 ({rss_url}): {e}")

        return items

    def _load_stored_item_guids(self) -> set[str]:
        """
        从本地文件加载先前存储的条目的 GUID。

        返回:
            set[str]: 存储的 GUID 集合。如果文件不存在或无法读取/解析，则返回空集合。
        """
        stored_guids = set()
        if os.path.exists(self.data_file_path):
            try:
                with open(self.data_file_path, "r", encoding="utf-8") as f:
                    stored_items = json.load(f)
                for item in stored_items:
                    # 确保 'guid' 键存在
                    if isinstance(item, dict) and "guid" in item and item["guid"]:
                        stored_guids.add(item["guid"])
            except json.JSONDecodeError:
                print(
                    f"解析 JSON 文件 '{self.data_file_path}' 失败。将视为空白历史记录。"
                )
            except IOError:
                print(f"读取文件 '{self.data_file_path}' 失败。将视为空白历史记录。")
        return stored_guids

    def _save_current_items(self, items: list[dict]):
        """
        将当前获取的条目列表保存到本地文件。

        参数:
            items (list[dict]): 要保存的条目字典列表。
        """
        try:
            with open(self.data_file_path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=4)
        except IOError:
            print(f"写入文件 '{self.data_file_path}' 失败。")
        except Exception as e:
            print(f"保存当前条目时发生未知错误: {e}")

    def get_new_items(
        self, rss_url: str = "https://linux.do/c/welfare/36.rss"
    ) -> list[dict]:
        """
        检查 RSS 订阅源中与先前存储的条目相比是否有新条目。
        保存当前获取的订阅条目以供下次检查。

        参数:
            rss_url (str, 可选): 要检查的 RSS 订阅源 URL。
                                 默认为 "https://linux.do/c/welfare/36.rss"。

        返回:
            list[dict]: 新条目的列表，每个条目是一个包含 'title' 和 'link' 的字典。
                        如果没有新条目或获取/解析失败，则返回空列表。
        """
        print(f"\n正在从 {rss_url} 获取 RSS 订阅...")
        current_items = self._fetch_and_parse_rss(rss_url)

        if not current_items:
            print("未能获取或解析 RSS 订阅，或订阅为空。未发现新条目。")
            return []

        print(f"成功获取 {len(current_items)} 个条目。正在加载已存储的条目...")
        stored_guids = self._load_stored_item_guids()
        print(f"已加载 {len(stored_guids)} 个已存储条目的 GUID。")

        new_items_info = []

        for item in current_items:
            if item.get("guid") and item["guid"] not in stored_guids:
                new_items_info.append({"title": item["title"], "link": item["link"]})

        if new_items_info:
            print(f"发现 {len(new_items_info)} 个新条目。")
        else:
            print("没有发现新条目。")

        # 保存所有当前获取的条目（包括新的和旧的），以便下次运行时进行比较
        print(f"正在保存 {len(current_items)} 个当前条目到 {self.data_file_path}...")
        self._save_current_items(current_items)

        return new_items_info


if __name__ == "__main__":
    # --- 使用示例 ---

    # 1. 指定一个本地目录来存储 RSS 数据
    #    请确保这个目录是可写的。
    #    脚本会在当前工作目录下创建一个名为 'rss_monitor_data' 的子目录。
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    storage_dir = os.path.join(current_script_path, "rss_monitor_data_output")

    # 2. 创建 RssMonitor 实例
    monitor = RssMonitor(local_storage_path=storage_dir)

    # 3. 指定 RSS 订阅 URL
    linuxdo_welfare_rss = "https://linux.do/c/welfare/36.rss"

    print(f"--- 首次运行或检查 '{linuxdo_welfare_rss}' ---")
    new_posts = monitor.get_new_items(rss_url=linuxdo_welfare_rss)

    if new_posts:
        print("\n发现以下新内容:")
        for i, post in enumerate(new_posts, 1):
            print(f"  新条目 {i}:")
            print(f"    标题: {post['title']}")
            print(f"    链接: {post['link']}")
        # 推送到飞书
        # 构建飞书富文本内容
        post_content_elements = []

        # 添加第一行文本
        post_content_elements.append([{"tag": "text", "text": "🚀 论坛更新"}])

        # 为每个新帖子添加内容
        for post in new_posts:
            title_element = [{"tag": "text", "text": f"标题: {post['title']}"}]
            link_element = [
                {"tag": "text", "text": "链接: "},
                {"tag": "a", "text": post["link"], "href": post["link"]},
            ]
            post_content_elements.append(title_element)
            post_content_elements.append(link_element)
            post_content_elements.append(
                [{"tag": "text", "text": "-----------------------"}]
            )  # 分隔

        feishu("🚀 论坛更新", post_content_elements)
    else:
        print("\n在此次检查中，没有发现新内容，或者所有内容都是已知的。")
