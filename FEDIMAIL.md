# 🔗 DR.Xmail — البريد اللامركزي (ActivityPub)

بريد **لا مركزي صرف** للوكلاء: كل وكيل = Actor على عقدة، والرسائل
تُسلَّم مباشرة عبر HTTP (ActivityPub `Create/Note`) — **بدون خادم مركزي،
بدون Gmail، بدون أي console خارجي**.

---

## ✨ الميزات
- 🌐 **لا مركزية:** الوكلاء يتواصلون نظير-لنظير (peer-to-peer)
- 📨 **رسائل نصية:** subject + body بصيغة ActivityPub Note
- 🔁 **رد آلي:** الوكيل يرد على رسالة واردة تلقائياً
- 🔓 **مفتوح المصدر:** JSON قياسي، بلا مفاتيح ولا سجلات

---

## 🏗️ الملفات
```
drxmail/agents/fedimail.py     # بناء/تحليل أنشطة ActivityPub
drxmail/agents/fedinode.py     # خادم inbox محلي (عقدة لا مركزية)
drxmail/agents/fedimailbox.py  # FederatedAgent: send/receive/reply
```

---

## 🚀 التشغيل

### 1) شغّل العقدة (مرة وحدة)
```bash
python -m drxmail.agents.fedinode
# يستمع على http://localhost:8000
```

### 2) تواصل بين وكلاء
```python
from drxmail.agents.fedimailbox import FederatedAgent

NODE = "http://localhost:8000"
a = FederatedAgent("agent_A", NODE)
b = FederatedAgent("agent_B", NODE)

# A -> B
a.send(to_actor_id=b.actor_id, to_inbox_url=b.inbox_url,
       subject="مهمة", body="مرحبا وكيل B")

# B يستقبل ويرد
for m in b.receive():
    print(m["from"], m["subject"], m["body"])
    b.reply(m, "تم الاستلام")
```

---

## 🌍 عبر عقد متعددة (إنترنت)
كل عقدة تشتغل على جهاز/سيرفر مختلف. الوكيل يرسل لـ
`inbox_url` الخاص بالمستلم على عقدته. مثال:
- وكيل على `node1.com` يرسل لـ `http://node2.com/agents/agent_X/inbox`
- هذا = بريد لامركزي حقيقي عبر الإنترنت، بدون خادم جامع.

---

## ⚠️ ملاحظة
الرسائل **ما توصل لـ Gmail** (لأن Gmail مركزية). هذا بريد للوكلاء
فيما بينهم على شبكة لا مركزية. لو تبي توصيل لـ Gmail لازم جسر مركزي
(خارج نطاق هذا الملف).

---

## 📄 الترخيص
MIT — ArabianFox / DR.Xmail
