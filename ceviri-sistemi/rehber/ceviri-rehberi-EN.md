# 🌐 Lato Translation Bot — User Guide

> **Bot:** @Latotry_bot
> **Location:** 🌐 Translation topic (Topic 146)
> **Languages:** 🇹🇭 Thai ↔ 🇹🇷 Turkish ↔ 🇬🇧 English

---

## 📌 What Does the Bot Do?

The Lato Translation Bot enables hotel staff to communicate instantly across different languages. When someone sends a voice or text message, the bot:

1. **Automatically detects** the language (Thai, Turkish, or English).
2. **Translates** the message into the other languages.
3. **Posts** the translation in the group for everyone to see.
4. If your voice is registered, it can **speak translations in your own voice**.

**Example:**
> Ahmet sends a voice message in Turkish → The bot translates it into Thai and English → Thai and English-speaking staff understand instantly.

---

## 🚀 How to Use It

### Sending a Voice Message
1. Go to the 🌐 **Translation** topic.
2. Press the Telegram microphone icon and speak.
3. The bot listens, detects your language, and translates it.

### Sending a Text Message
1. Go to the 🌐 **Translation** topic.
2. Type your message.
3. The bot detects the language and translates it.

> 💡 **Tip:** Speak naturally and clearly. You don't need to speak slowly.

---

## 🎙️ Voice Registration

To have the bot speak translations **in your own voice**, you need to register your voice.

### Step-by-Step Registration:

| Step | What to Do |
|------|------------|
| **1** | Send the `/register` command in the 🌐 Translation topic |
| **2** | The bot will ask for your name — type your name or nickname (e.g., `Ahmet`) |
| **3** | The bot will ask for a voice sample — speak naturally for **15–30 seconds** |

### What Should I Say in the Voice Sample?

Anything! Here's an example:

> *"Hello, my name is Ahmet. I work at the Lato Hotel as a receptionist. My daily tasks include welcoming guests, handling room reservations, and answering phone calls. I love my job and I always try to provide the best service to our guests."*

**Important:**
- ✅ Speak calmly and clearly
- ✅ Record in a quiet place with no background noise
- ✅ Speak for at least 15 seconds, at most 30 seconds
- ❌ Don't whisper
- ❌ Don't speak too fast

---

## 🧬 How Voice Cloning Works

The bot uses **ElevenLabs** technology to clone your voice:

1. When you submit your voice sample, the system learns your voice characteristics.
2. From then on, when the bot translates on your behalf, it **speaks in your voice**.
3. Example: When a Thai staff member speaks in Thai, the bot translates it into Turkish and reads the translation **in your voice**.

> 🔒 Your voice is used only within this bot. It is not shared with any other service.

---

## 🔤 Accent Corrections

Sometimes the bot may mishear special names or local words. You can teach it the correct pronunciation:

### Command:
```
/accent add wrongword correctword
```

### Examples:
```
/accent add phuket puket
/accent add sawatdee savatdi
/accent add kapib kapik
```

This way, the bot pronounces these words correctly every time.

### View Existing Corrections:
```
/accent list
```

### Remove a Correction:
```
/accent remove wrongword
```

---

## 📋 Command List

| Command | Description |
|---------|-------------|
| `/register` | Register your voice — the bot learns your voice tone |
| `/myvoice` | Shows the status of your voice registration (registered, ready) |
| `/accent` | Manage accent corrections (`/accent add`, `/accent list`, `/accent remove`) |
| `/languages` | Lists the languages supported by the bot |
| `/speakers` | Shows the list of people who have registered their voices |
| `/help` | Shows all commands and usage information |

---

## 🔒 Privacy

- 🔐 Your voice samples are **stored locally on the hotel server**.
- 🚫 Voice samples are not shared with any third-party service (except ElevenLabs for cloning).
- 👤 The bot uses your voice only for translation purposes.
- 🗑️ You can request to have your voice sample deleted at any time — use `/help` to contact support.

---

## ❓ Frequently Asked Questions

**Q: Does the bot translate every message as voice?**
A: No. The bot first provides a text translation. If your voice is registered and voice output is appropriate, it also provides audio.

**Q: Can I register my voice in multiple languages?**
A: For now, one voice registration per person is sufficient. The bot applies your voice tone to all languages.

**Q: I want to update my voice sample, what should I do?**
A: Simply use `/register` again. The new recording replaces the old one.

**Q: The bot made a wrong translation, what should I do?**
A: Keep using the bot. You can use the `/accent` command for pronunciation corrections.

---

## 📞 Support

If you have questions, write in the 🌐 Translation topic or use the `/help` command.

**Happy communicating! 🌟**

---

*Lato Translation Bot — Phuket, Thailand*
*@Latotry_bot*
