# 🤖 DR.Xmail — منصة البريد للوكلاء (Agents Mail Platform)

> كل وكيل AI ياخذ **إيميله الخاص**، يسجّل فيه، يرسل، يستقبل، ويرد — ومعلوماته محفوظة خاصّة فيه.

نظام بريد مفتوح المصدر مبني للوكلاء الذكيين. بدل ما تشاركون حساب واحد،
كل وكيل ينشئ هويته المستقلة ويحرسها بنفسه.

---

## ✨ الميزات

- 🆔 **هوية خاصة لكل وكيل** — إيميل + كلمة مرور محفوظة في ملف محلي آمن خاص فيه.
- 📥 **استقبال فوري** عبر Mail.tm (مجاني، بدون مفتاح).
- 📤 **إرسال** عبر SMTP الخاص بالوكيل (Gmail/Outlook/أي حساب).
- 🔁 **رد آلي** على الرسائل الواردة.
- 🔑 **استخراج OTP/روابط** آلي من صندوق الوكيل.
- 💾 **حفظ واسترجاع** — الوكيل يقدر يحمّل هويته بعد إعادة التشغيل.
- 🖥️ **واجهة Streamlit** لإدارة كل الوكلاء.

---

## 🏗️ البنية

```
drxmail/agents/
├── store.py      # مخزن الهويات (يحفظ ايميل+باسورد لكل وكيل)
├── mailbox.py    # AgentMailbox: إنشاء/تحميل/إرسال/استقبال/رد
├── senders.py    # طبقة إرسال SMTP قابلة للتوصيل (pluggable)
├── cli.py        # سطر أوامر لإدارة الوكلاء
└── __init__.py

E:\ArabianFox\agents_mail\identities\     # ملفات هويات الوكلاء (خاصة)
```

---

## 🚀 الاستخدام السريع

### إنشاء وكيل + إرسال
```python
from drxmail.agents.mailbox import AgentMailbox

# وكيل جديد (يُنشئ إيميله ويحفظه)
mb = AgentMailbox()
mb.create("agent_01", smtp_cfg={
    "host": "smtp.gmail.com", "port": 587,
    "user": "you@gmail.com", "password": "app_password"
})
print(mb.email, mb.password)   # محفوظ في agents_mail/identities/agent_01.json

# لاحقاً: تحميل الوكيل
mb2 = AgentMailbox()
mb2.load("agent_01")
mb2.send("friend@x.com", "Hello", "from my agent")
```

### CLI
```bash
python -m drxmail.agents.cli create agent_01 --smtp '{"host":"smtp.gmail.com","port":587,"user":"you@gmail.com","password":"app"}'
python -m drxmail.agents.cli list
python -m drxmail.agents.cli inbox agent_01
python -m drxmail.agents.cli send agent_01 --to a@b.com --subject hi --body hello
```

### الواجهة
```bash
streamlit run drxmail/ui/agents_app.py
```

---

## ⚠️ ملاحظة مهمة عن الإرسال
مواقع البريد المؤقت (Mail.tm وغيرها) **معطّلة الإرسال** من السيرفر.
لذلك الإرسال يتم عبر **SMTP حساب الوكيل نفسه** (تضيفه بملف هويته).
المرسل الفعلي = حساب SMTP، وصندوق الاستقبال = إيميل Mail.tm الخاص بالوكيل.

---

## 📄 الترخيص
MIT — ArabianFox / DR.Xmail
