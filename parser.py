from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
from urllib.parse import urljoin, urlparse

import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def create_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--start-maximized")
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    return driver

def fetch_page_source(driver: webdriver.Chrome, url: str, wait: float = 5.0) -> str:
    driver.get(url)
    time.sleep(wait)
    return driver.page_source


def get_whatsapp_link(driver, container, timeout=60):
    try:
        chat_btn = container.find_element(
            By.CSS_SELECTOR,
            "a.WorkerControls-Control_chat button.Button2"
        )

        print("HTML кнопки:", chat_btn.get_attribute("outerHTML"))
        if not chat_btn:
            print(f"Кнопка чат не найдена, скип")
            return None

        driver.execute_script("arguments[0].scrollIntoView(true);", chat_btn)
        driver.execute_script("arguments[0].click();", chat_btn)
        print("✅ Кнопка 'Чат' нажата")

        try:
            element = WebDriverWait(driver, timeout).until(
                EC.any_of(
                    # EC.visibility_of_element_located((By.CSS_SELECTOR, "table.SocialLinkList")),
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.Popup2.Popup2_visible")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.ya-chat-popup.ya-chat-popup_visible"))
                )
            )
        except Exception:
            print("❌ Ни таблицы, ни окна чата не появилось")
            return None

        href = None

        if "Popup2_visible" in element.get_attribute("class"):
            try:
                table = element.find_element(By.CSS_SELECTOR, "table.SocialLinkList")
                wa_link = table.find_element(By.CSS_SELECTOR, "a.SocialLinkList-whatsapp")
                href = wa_link.get_attribute("href")
                print(f"✅ WhatsApp ссылка: {href}")

                # Скрываем таблицу через JS
                driver.execute_script("arguments[0].style.display='none';", table)
                print("🔒 Таблица скрыта вручную через JS")

                # Повторный клик на кнопку "Чат", чтобы закрыть окно полностью
                driver.execute_script("arguments[0].click();", chat_btn)
                print("🔒 Чат закрыт повторным кликом на кнопку")
                return href

            except Exception:
                print("❌ Ссылки WhatsApp нет в SocialLinkList")
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


def parse_whatsapp_link(link: str) -> str | None:
    if not link:
        return None
    try:
        path = urlparse(link).path  # -> "/79191376017"
        phone_digits = re.sub(r"\D", "", path)  # -> "79191376017"

        if not phone_digits:
            return None

        if phone_digits.startswith("8"):
            phone_digits = "7" + phone_digits[1:]

        return phone_digits
    except Exception as e:
        print(f"❌ Ошибка парсинга WhatsApp ссылки: {e}")
        return None

def parser_data(target_url: str, limit: int=None, headless=False):
    driver = create_driver(headless=headless)
    try:
        url = target_url
        info = []

        while url:
            html = fetch_page_source(driver, url, wait=5)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.WorkersListBlendered-WorkerCard"))
            )
            
            # containers_selenium = driver.find_elements(By.CSS_SELECTOR, "div.WorkersListBlendered-WorkerCard")
            containers_selenium = driver.find_elements(
                By.CSS_SELECTOR, "div.WorkersListBlendered-WorkerCard.Gap.Gap_bottom_l"
            )

            
            for container in containers_selenium:
                try:
                    if "WebBanner" in container.get_attribute("class"):
                        print(f"⚠️ В контейнере реклама, пропускаем. HTML: {container.get_attribute('outerHTML')[:200]}...")
                        continue
                    # name_element = container.find_element(By.CSS_SELECTOR, "a.WorkerCard-Title")
                    # name_element = container.find_element(By.CSS_SELECTOR, "a.WorkerCard-Title, a.WorkerCard-Title.WorkerCard-Title_withLabel")

                    try:
                        name_element = container.find_element(By.CSS_SELECTOR, "a.WorkerCard-Title")
                    except Exception:
                        container_html = container.get_attribute("outerHTML")[:500]
                        print(f"⚠️ В контейнере нет имени, скипаем. HTML: {container_html}...")
                        continue

                    geo_element = container.find_element(By.CSS_SELECTOR, "div.WorkerGeo-Address")
                    
                    name = name_element.text.strip()
                    geo = geo_element.text.strip()
                    phone_html = get_whatsapp_link(driver, container)
                    phone = parse_whatsapp_link(phone_html) if phone_html else None

                    print(phone)
                    
                    if name and phone:
                        info.append({
                            "name": name,
                            "geo": geo,
                            "phone": phone
                        })
                
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
