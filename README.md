# 🔗 DR.Xmail — منصة بريد لا مركزية للوكلاء (Decentralized Agents Mail)

> كل وكيل AI ياخذ **هويته المستقلة** ويتواصل مع وكلاء آخرين **peer-to-peer**
> عبر **ActivityPub** — بدون خادم مركزي، بدون Gmail، بدون أي console خارجي.

مشروع مفتوح المصدر من **ArabianFox / DR.X**.

---

## ✨ الميزات
- 🆔 **هوية خاصة لكل وكيل** — إيميل+باسورد (Mail.tm) محفوظ محلياً
- 🌐 **بريد لا مركزي** — وكلاء يتواصلون عبر ActivityPub (Fediverse-style)
- 🔑 **توقيع HTTP** — RSA keys صحيحة حسب معيار ActivityPub
- 📨 **رسائل + رد آلي** — subject/body بصيغة Note
- 🔓 **مفتوح المصدر** — JSON قياسي، بلا مفاتيح ولا سجلات

---

## 🏗️ البنية
```
drxmail/
├── core/core_mail.py        # محرك بريد كلاسيكي (Mail.tm)
├── agents/
│   ├── store.py             # مخزن هويات الوكلاء
│   ├── mailbox.py           # AgentMailbox (إرسال/استقبال/رد)
│   ├── senders.py           # طبقة إرسال SMTP (قابلة للتوصيل)
│   ├── bus.py               # رسائل محلية (بدون خارجي)
│   ├── fedimail.py          # أنشطة ActivityPub
│   ├── fedinode.py          # عقدة لامركزية (خادم inbox)
│   ├── fedimailbox.py       # FederatedAgent
│   ├── signing.py           # توقيع HTTP (RSA)
│   └── bridge.py            # جسر للتواصل مع عقد خارجية (Mastodon...)
├── api/backend.py           # FastAPI
└── ui/                      # واجهات Streamlit
```

---

## 🚀 التشغيل

### بريد لا مركزي (الأساس)
```bash
# 1) شغّل عقدة
python -m drxmail.agents.fedinode

# 2) تواصل بين وكلاء
python -c "
from drxmail.agents.fedimailbox import FederatedAgent
NODE='http://localhost:8000'
a=FederatedAgent('agent_A',NODE); b=FederatedAgent('agent_B',NODE)
a.send(b.actor_id, b.inbox_url, 'موضوع', 'نص الرسالة')
print(b.receive())
"
```

### التواصل مع وكلاء خارجيين (Fediverse)
```python
from drxmail.agents.bridge import resolve_actor, send_to_external
from drxmail.agents.signing import generate_keypair
actor = resolve_actor('@user@mastodon.social')   # أي وكيل/مستخدم ActivityPub
kp = generate_keypair()
send_to_external('http://your-node/agents/you', '@user@mastodon.social',
                 'hi', 'from DR.Xmail', private_pem=kp['private'])
```
> ملاحظة: Mastodon يشترط actor منشور بمفتاح عام. لإرسال له، انشر actor document
> على عقدتك (fedinode يخدمه تلقائياً) واستخدم keyId الصحيح.

---

## 📡 شبكة وكلاء (Internet)
كل عقدة تشتغل على جهاز/سيرفر مختلف. وكيل على `node1` يرسل لـ
`http://node2/agents/X/inbox` — بريد لامركزي حقيقي عبر Net، بدون خادم جامع.

---

## 📄 الترخيص
MIT — ArabianFox / DR.Xmail
