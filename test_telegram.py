import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

async def test_telegram():
    print("=" * 50)
    print("TELEGRAM BOT TEST")
    print("=" * 50)
    
    # Check credentials
    if not TELEGRAM_BOT_TOKEN:

        print("[X] TELEGRAM_BOT_TOKEN bulunamadi!")
        print("   .env dosyasina ekleyin:")
        print("   TELEGRAM_BOT_TOKEN=your_token_here")
        return False
    
    if not TELEGRAM_CHAT_ID:
        print("[X] TELEGRAM_CHAT_ID bulunamadi!")
        print("   .env dosyasina ekleyin:")
        print("   TELEGRAM_CHAT_ID=your_chat_id_here")
        return False
    
    print(f"[OK] Token: {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"[OK] Chat ID: {TELEGRAM_CHAT_ID}")
    print()
    
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Test 1: Get bot info
        print("Test 1: Bot bilgilerini al...")
        me = await bot.get_me()
        print(f"[OK] Bot adi: @{me.username}")
        print(f"[OK] Bot ID: {me.id}")
        print()
        
        # Test 2: Send test message
        print("Test 2: Test mesaji gonder...")
        msg = await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="Test Mesaji\n\nTelegram bot calisiyor!"
        )
        print(f"[OK] Mesaj gonderildi! Message ID: {msg.message_id}")
        print()
        
        # Test 3: Get updates
        print("Test 3: Son mesajlari kontrol et...")
        updates = await bot.get_updates(limit=5)
        if updates:
            print(f"[OK] {len(updates)} mesaj bulundu")
            for update in updates[-3:]:
                if update.message:
                    print(f"   - {update.message.from_user.first_name}: {update.message.text[:30]}...")
        else:
            print("[!] Henuz mesaj yok. Botunuza /start yazin!")
        print()
        
        print("=" * 50)
        print("[OK] TUM TESTLER BASARILI!")
        print("=" * 50)
        print()
        print("Şimdi yapabilecekleriniz:")
        print("1. Telegram'da botunuza mesaj yazın")
        print("2. python app.py ile uygulamayı başlatın")
        print("3. Visitor'dan mesaj gönderin")
        print("4. Telegram'da bildirimi görün")
        print("5. Telegram'dan reply yapın")
        print("6. Visitor'da yanıtı görün")
        
        return True
        
    except Exception as e:
        print(f"[X] HATA: {e}")
        print()
        print("Olasi sorunlar:")
        print("1. Token yanlis olabilir")
        print("2. Chat ID yanlis olabilir")
        print("3. Botunuza /start yazmadiniz")
        print("4. Internet baglantisi yok")
        return False

if __name__ == '__main__':
    asyncio.run(test_telegram())
