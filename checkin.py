"""
Check-in otomasyonu — Playwright ile tarayıcı kontrolü
Her havayolu için ayrı fonksiyon
"""
import logging
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class CheckinService:

    async def do_checkin(self, airline: str, pnr: str, lastname: str) -> dict:
        """Havayoluna göre doğru check-in fonksiyonunu çağırır."""
        handlers = {
            "Pegasus": self._checkin_pegasus,
            "THY (Turkish Airlines)": self._checkin_thy,
            "SunExpress": self._checkin_sunexpress,
            "AnadoluJet": self._checkin_anadolujet,
        }
        handler = handlers.get(airline)
        if not handler:
            return {"success": False, "error": f"Desteklenmeyen havayolu: {airline}"}

        try:
            return await handler(pnr, lastname)
        except Exception as e:
            logger.error(f"Check-in hatası ({airline} {pnr}): {e}")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------ #
    #  PEGASUS                                                              #
    # ------------------------------------------------------------------ #
    async def _checkin_pegasus(self, pnr: str, lastname: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto("https://www.flypgs.com/online-check-in", timeout=30000)
                await page.wait_for_load_state("networkidle")

                # PNR gir
                await page.fill('input[name="bookingCode"], input[id*="pnr"], input[placeholder*="PNR"]', pnr)
                # Soyad gir
                await page.fill('input[name="lastName"], input[id*="lastName"], input[placeholder*="yadınız"]', lastname)
                # Devam et
                await page.click('button[type="submit"], button:has-text("Sorgula"), button:has-text("Devam")')
                await page.wait_for_load_state("networkidle", timeout=15000)

                # Check-in butonunu ara
                checkin_btn = page.locator('button:has-text("Check-in"), button:has-text("Checkin")')
                if await checkin_btn.count() > 0:
                    await checkin_btn.first.click()
                    await page.wait_for_load_state("networkidle")

                # Koltuk bilgisini al
                seat = await self._extract_seat(page)

                # Boarding pass URL
                bp_url = await self._get_boarding_pass_url(page)

                return {"success": True, "seat": seat, "boarding_pass_url": bp_url}

            except PlaywrightTimeout:
                return {"success": False, "error": "Havayolu sitesi zaman aşımına uğradı."}
            finally:
                await browser.close()

    # ------------------------------------------------------------------ #
    #  THY                                                                  #
    # ------------------------------------------------------------------ #
    async def _checkin_thy(self, pnr: str, lastname: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto("https://www.turkishairlines.com/tr-int/flights/manage-booking/", timeout=30000)
                await page.wait_for_load_state("networkidle")

                await page.fill('input[id*="bookingCode"], input[name*="pnr"]', pnr)
                await page.fill('input[id*="lastName"], input[name*="lastName"]', lastname)
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle", timeout=15000)

                checkin_btn = page.locator('a:has-text("Check-in"), button:has-text("Check-in")')
                if await checkin_btn.count() > 0:
                    await checkin_btn.first.click()
                    await page.wait_for_load_state("networkidle")

                seat = await self._extract_seat(page)
                bp_url = await self._get_boarding_pass_url(page)

                return {"success": True, "seat": seat, "boarding_pass_url": bp_url}

            except PlaywrightTimeout:
                return {"success": False, "error": "Havayolu sitesi zaman aşımına uğradı."}
            finally:
                await browser.close()

    # ------------------------------------------------------------------ #
    #  SUNEXPRESS                                                           #
    # ------------------------------------------------------------------ #
    async def _checkin_sunexpress(self, pnr: str, lastname: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto("https://www.sunexpress.com/tr/check-in/", timeout=30000)
                await page.wait_for_load_state("networkidle")

                await page.fill('input[name*="pnr"], input[id*="pnr"]', pnr)
                await page.fill('input[name*="lastName"], input[id*="lastName"]', lastname)
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle", timeout=15000)

                seat = await self._extract_seat(page)
                bp_url = await self._get_boarding_pass_url(page)

                return {"success": True, "seat": seat, "boarding_pass_url": bp_url}

            except PlaywrightTimeout:
                return {"success": False, "error": "Havayolu sitesi zaman aşımına uğradı."}
            finally:
                await browser.close()

    # ------------------------------------------------------------------ #
    #  ANADOLUJET                                                           #
    # ------------------------------------------------------------------ #
    async def _checkin_anadolujet(self, pnr: str, lastname: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto("https://www.anadolujet.com/tr/check-in", timeout=30000)
                await page.wait_for_load_state("networkidle")

                await page.fill('input[name*="pnr"], input[id*="pnr"]', pnr)
                await page.fill('input[name*="lastName"], input[id*="lastName"]', lastname)
                await page.click('button[type="submit"]')
                await page.wait_for_load_state("networkidle", timeout=15000)

                seat = await self._extract_seat(page)
                bp_url = await self._get_boarding_pass_url(page)

                return {"success": True, "seat": seat, "boarding_pass_url": bp_url}

            except PlaywrightTimeout:
                return {"success": False, "error": "Havayolu sitesi zaman aşımına uğradı."}
            finally:
                await browser.close()

    # ------------------------------------------------------------------ #
    #  Yardımcı fonksiyonlar                                               #
    # ------------------------------------------------------------------ #
    async def _extract_seat(self, page) -> str:
        """Sayfadan koltuk numarasını çekmeye çalışır."""
        selectors = [
            '[class*="seat"]', '[id*="seat"]',
            'text=/\d+[A-Z]/', '[class*="boarding"]'
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    text = await el.text_content()
                    if text:
                        return text.strip()
            except Exception:
                continue
        return "Belirtilmedi"

    async def _get_boarding_pass_url(self, page) -> str:
        """Boarding pass PDF veya indirme linkini bul."""
        selectors = [
            'a[href*="boarding"], a[href*="pass"], a[href*=".pdf"]',
            'button:has-text("İndir"), button:has-text("PDF")',
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    href = await el.get_attribute("href")
                    if href:
                        return href
            except Exception:
                continue
        return None
