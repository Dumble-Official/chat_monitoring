\---

title: Gym Comment Classifier
emoji: 🏋️
colorFrom: blue
colorTo: green
sdk: docker
app\_port: 7860
pinned: false
---

# Gym Comment Classifier API

FastAPI endpoint يصنف التعليقات والبوستات إلى 3 تصنيفات:

|Label|Action|المعنى|
|-|-|-|
|`Clean`|`publish`|ينشر عادي|
|`Offensive`|`publish`|ينشر بس يُسجَّل في الـ DB|
|`Toxic`|`delete`|يُحذف من الـ app ويُحفظ في الـ DB|

\---

## Endpoints

### `POST /classify`

```json
{
  "text": "النادي ممتاز والخدمة رائعة",
  "post\_id": "abc123"
}
```

**Response:**

```json
{
  "text": "النادي ممتاز والخدمة رائعة",
  "post\_id": "abc123",
  "label": "Clean",
  "action": "publish",
  "confidence": {
    "Clean": 0.9512,
    "Offensive": 0.0312,
    "Toxic": 0.0176
  }
}
```

### `POST /classify/batch`

نفس الشيء بس بتبعت list فيها لحد 50 تعليق.

### `GET /health`

للتأكد إن السيرفر شغال.

\---

## 

