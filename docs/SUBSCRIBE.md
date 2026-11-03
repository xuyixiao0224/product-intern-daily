# 邮件订阅怎么发

**不要用私人 Gmail / QQ 邮箱群发。** 会进垃圾箱、触发限流、泄露个人地址，也不符合 ESP 条款。

## 推荐：Buttondown（适合 0–1000 订阅）

- 免费档约 100 订阅；
- 自带 double opt-in、退订、隐私页；
- 私有静态页/本地页面可直接嵌表单；
- 把 `docs/subscribe.html` 里的 `yixiao` 换成你的用户名。

发送：

- 在 Buttondown 后台粘贴 `exports/digest.html` 发送；或
- 用 `--provider webhook` 把 digest POST 到你的自动化（Zapier/Make/自建）。

## Resend（适合已有域名/列表）

- 免费约 3k 封/月；
- 需要验证自有域名（SPF/DKIM/DMARC）；
- 本仓库 `scripts/send_digest.py --provider resend --to you@example.com` 只用于测试发送；
- 给真实订阅者发，需要接 Resend Audience/Broadcast 或你自己的订阅表。

```bash
RESEND_API_KEY=... DIGEST_FROM=digest@yourdomain.com \
  python scripts/send_digest.py --provider resend --to you@example.com
```

## 自托管：Listmonk

- 自己的 SMTP（Amazon SES/Postmark/Mailgun）；
- 无按订阅数计费；
- 需要服务器、域名、退订/隐私页。

## 合规底线

- double opt-in；
- 每封都有退订；
- 隐私政策：收集什么、为什么、保存多久；
- 不卖给第三方；
- 中国境内外都注意个人信息保护（PIPL/GDPR）；
- 只发“公开帖子里的投递方式”，不群发私人邮箱。
