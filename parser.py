from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

import time
import tempfile
import time
import random
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from utils import parse_whatsapp_link

def create_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--remote-debugging-port={random.randint(9000, 9999)}")
    
    options.add_argument("--start-maximized")
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def fetch_page_source(driver: webdriver.Chrome, url: str, wait: float = 5.0) -> str:
    driver.get(url)
    time.sleep(wait)
    return driver.page_source


def get_whatsapp_link(driver: webdriver.Chrome, container, timeout=60):
    try:
        old_popups = driver.find_elements(
            By.CSS_SELECTOR,
            "div.Popup2.Popup2_visible.WorkerControls-MessengersPopup"
        )
        if old_popups:
            for popup in old_popups:
                driver.execute_script("arguments[0].remove();", popup)
            print(f"🗑️ Удалено {len(old_popups)} старых Popup2 из DOM перед кликом")

        try:
            chat_btn = container.find_element(
                By.CSS_SELECTOR,
                "a.WorkerControls-Control_chat button.Button2"
            )
        except Exception:
            print("❌ Кнопка Чат не найдена")
            return None
        
        try:
            adv_div = container.find_element(
                By.CSS_SELECTOR,
                "div.Text.Text_fontSize_s.Text_lineHeight_s.Text_color_greyDark.TextBlock.WorkerCard-AdvWarning"
            )
        except NoSuchElementException:
            adv_div = None

        main_window = driver.current_window_handle
        before_click = set(driver.window_handles)


        # driver.execute_script("arguments[0].scrollIntoView(true);", chat_btn)
        driver.execute_script("arguments[0].click();", chat_btn)
        print("✅ Кнопка 'Чат' нажата")

        if adv_div:
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: len(d.window_handles) > len(before_click)
                )
            except TimeoutException:
                print("⚠️ Новая вкладка не открылась")
                new_windows = []
            else:
                after_click = set(driver.window_handles)
                new_windows = after_click - before_click

            for w in new_windows:
                driver.switch_to.window(w)
                driver.close()
                print(f"🗑️ Закрыта новая вкладка {w}")

            driver.switch_to.window(main_window)

        try:
            element = WebDriverWait(driver, timeout).until(
                EC.any_of(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.Popup2.Popup2_visible")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.ya-chat-popup.ya-chat-popup_visible"))
                )
            )
        except Exception as e:
            print("❌ Ни таблицы, ни окна чата не появилось")
            
            try:
                html = driver.find_element(By.TAG_NAME, "body").get_attribute("outerHTML")
                print(f"Причина: {e}\nТекущий HTML body:\n{html[:2000]}...")  # Ограничиваем вывод до первых 2000 символов
            except Exception as inner_e:
                print(f"Не удалось получить HTML для дебага: {inner_e}")
            
            return None

        href = None

        if "Popup2_visible" in element.get_attribute("class"):
            try:
                # Ждём появления таблицы
                table = WebDriverWait(element, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.SocialLinkList"))
                )

                wa_link = WebDriverWait(table, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.SocialLinkList-whatsapp"))
                )

                href = wa_link.get_attribute("href")
                print(f"✅ WhatsApp ссылка: {href}")
                popups = driver.find_elements(
                    By.CSS_SELECTOR,
                    "div.Popup2.Popup2_visible.WorkerControls-MessengersPopup"
                )

                for popup in popups:
                    driver.execute_script("arguments[0].remove();", popup)
                print(f"🗑️ Удалено {len(popups)} Popup2 из DOM")

                WebDriverWait(driver, 5).until_not(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.Popup2.Popup2_visible.WorkerControls-MessengersPopup")
                    )
                )
                return href

            except Exception as e:
                html_snippet = element.get_attribute("outerHTML")
                print(f"❌ Ссылки WhatsApp нет в SocialLinkList: {e} HTML:\n{html_snippet}")
                return None
            

        chat_popups = driver.find_elements(By.CSS_SELECTOR, "div.ya-chat-popup.ya-chat-popup_visible")
        if chat_popups:
            driver.execute_script("arguments[0].style.display='none';", chat_popups[0])
            print("🔒 Чат скрыт вручную через JS")
        else:
            print("⚠️ Чат с классом ya-chat-popup_visible не найден, ничего не скрываем")

    except Exception as e:
        print(f"❌ Ошибка при поиске WhatsApp: {e}")
        return None



def parser_data(target_url: str, limit: int=None, headless=False):
    driver = create_driver(headless=headless)
    try:
        url = target_url
        info = []

        while url:
            print(f"Делаем запрос на: {url}")
            fetch_page_source(driver, url, wait=5)
            print(f"Запрос выполнен, страница открыта.")
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.WorkersListBlendered-WorkerCard"))
            )
            
            containers_selenium = driver.find_elements(
                By.CSS_SELECTOR, "div.WorkersListBlendered-WorkerCard.Gap.Gap_bottom_l"
            )

            for container in containers_selenium:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
                    time.sleep(0.5)

                    if "WebBanner" in container.get_attribute("class"):
                        print(f"⚠️ В контейнере реклама, пропускаем...")
                        continue

                    try:
                        name_element = container.find_element(By.CSS_SELECTOR, "a.WorkerCard-Title")
                    except Exception:
                        container_html = container.get_attribute("outerHTML")[:500]
                        print(f"⚠️ В контейнере нет имени, скипаем. HTML: {container_html}")
                        continue
                    try:
                        geo_element = container.find_element(By.CSS_SELECTOR, "div.WorkerGeo-Address")
                    except Exception:
                        container_html = container.get_attribute("outerHTML")[:500]
                        print(f"⚠️ В контейнере нет гео, скипаем. HTML: {container_html}")

                    
                    name = name_element.text.strip()
                    geo = geo_element.text.strip()

                    print(f"Получаем телефон пользователя: {name}")

                    phone_html = get_whatsapp_link(driver, container)
                    phone = parse_whatsapp_link(phone_html) if phone_html else None
                    
                    if name and phone:
                        entry = {
                            "name": name,
                            "geo": geo,
                            "phone": phone
                        }
                        info.append(entry)
                        print(entry)
                
                    if limit and len(info) >= limit:
                        return info
                
                except Exception as e:
                    print(f"⚠️ Ошибка при обработке контейнера: {e}")
                    continue
            try:
                pager = driver.find_element(By.CSS_SELECTOR, "div.Pager.Serp-Pager")
                next_link = pager.find_element(By.CSS_SELECTOR, "a[rel='next']")
                url = urljoin("https://uslugi.yandex.ru", next_link.get_attribute("href"))
            except:
                url = None

        return info

    finally:
        driver.quit()
