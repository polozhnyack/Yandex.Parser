import re
from urllib.parse import urljoin, urlparse





def parse_whatsapp_link(link: str) -> str | None:
    if not link:
        return None
    try:

        path = urlparse(link).path  # -> "/79191376017" или "/9287626363"
        phone_digits = re.sub(r"\D", "", path)

        if not phone_digits:
            return None

        if len(phone_digits) == 10:
            phone_digits = "7" + phone_digits
        elif len(phone_digits) == 11 and phone_digits.startswith("8"):
            phone_digits = "7" + phone_digits[1:]
        elif len(phone_digits) == 11 and phone_digits.startswith("7"):
            pass
        else:
            return None

        return phone_digits

    except Exception as e:
        print(f"❌ Ошибка парсинга WhatsApp ссылки: {e}")
        return None