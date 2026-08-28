# 🚀 دليل نشر DR.Xmail (مجاني 100% — بدون أي خدمة مدفوعة)

الهدف: وكيل DR.Xmail يرسل رسالة توصل **فعلاً** لـ `r6504r@gmail.com`
عبر خدمات **مجانية بالكامل** لا تطلب بطاقة ولا عنوان مؤسسة.

---

## 💡 الاستراتيجية المجانية الصافية
- **السيرفر:** Render Free (مجاني، GitHub login فقط)
- **الإرسال:** Gmail SMTP عبر حسابك `r6504r@gmail.com` + **App Password**
  (مجاني 100%، وموثّق عند Gmail → توصل للـ Inbox مو السبام)
- **الاستقبال + OTP:** Mail.tm (داخل مشروعنا، مجاني بدون مفتاح)
- **دومين:** غير مطلوب — نرسل باسم `r6504r@gmail.com`

> ❌ لا Brevo، لا AgentMail، لا أي خدمة تطلب عنوان مؤسسة أو دفعة.

---

## 1️⃣ تجهيز Gmail App Password (مجاني)
1. فعّل **2-Step Verification** على `r6504r@gmail.com`:
   https://myaccount.google.com/security
2. ادخل: Security → App passwords → أنشئ كلمة مرور باسم "DRXmail"
3. تاخذ **16 حرف** (مثل `abcd efgh ijkl mnop`) — هذا هو الـ password للإرسال.

## 2️⃣ ربط مشروعنا بالإرسال
في ملف هوية الوكيل (`E:\ArabianFox\agents_mail\identities\<id>.json`)
أو عبر CLI:
```bash
python -m drxmail.agents.cli create agent_01 --smtp '{"backend":"smtp","host":"smtp.gmail.com","port":587,"user":"r6504r@gmail.com","password":"XXXX XXXX XXXX XXXX"}'
```
(الـ user = بريدك، الـ password = App Password الـ 16 حرف)

## 3️⃣ السيرفر (Render مجاني)
1. سجّل: https://render.com (بـ GitHub، بدون كريدت كارد)
2. ارفع المشروع على GitHub.
3. New > Web Service → Connect الريبو → Render يقرأ `render.yaml`.
4. اضغط Deploy → رابط: `https://drxmail-agents.onrender.com`

## 4️⃣ اختبار التوصيل الحقيقي
```bash
python -m drxmail.agents.cli send agent_01 --to r6504r@gmail.com --subject اختبار --body مرحبا من وكيل
```
الرسالة توصل لـ `r6504r@gmail.com` مباشرة (Inbox).

---

## 📊 التكلفة
| خدمة | التكلفة |
|------|---------|
| Render | $0 (Free) |
| Gmail SMTP | $0 (حسابك) |
| Mail.tm | $0 |
| **الإجمالي** | **$0** ✅ |

ملكك 100%، مفتوح المصدر، بدون أي console خارجي.
