# Vision MVP Validation / Валидация Vision для MVP

Дата baseline: 2026-08-31

## Назначение

Этот документ фиксирует воспроизводимую минимальную проверку multi-food pipeline. Она не является
доказательством клинической, нутриционной или production-точности и не заменяет расширенный
validation dataset.

## Модели

Detector:

- `IDEA-Research/grounding-dino-tiny`;
- revision `a2bb814dd30d776dcf7e30523b00659f4f141c71`;
- source: https://huggingface.co/IDEA-Research/grounding-dino-tiny;
- official implementation: https://github.com/IDEA-Research/GroundingDINO;
- license: Apache-2.0;
- artifact: `model.safetensors`.

Classifier:

- `nateraw/food`;
- revision `ddbd0f9ed493f03fc6a45527e5e52904161d3e09`;
- source: https://huggingface.co/nateraw/food;
- license модели по model card: Apache-2.0;
- task: Food-101 dish classification;
- artifact: `model.safetensors`.

Training-data provenance и права на исходные изображения требуют отдельной юридической проверки до
коммерческого production launch. Лицензия model/repository не устраняет этот риск автоматически.

## Fixture

В репозитории хранится официальная demonstration figure FoodSeg103 и manifest с восемью
multi-food crop:

- `services/vision/fixtures/validation/foodseg103_examples.png`;
- `services/vision/fixtures/validation/foodseg103_manifest.json`;
- `services/vision/fixtures/validation/ATTRIBUTION.md`.

FoodSeg103 project указывает Apache-2.0. Fixture не содержит фото пользователей FoodAI и не
используется для обучения. Восемь примеров покрывают продукты, напитки, смешанные блюда и тарелки с
несколькими ингредиентами, но выборка слишком мала для production accuracy claims.

## Метрики

- `multi_region_rate`: доля multi-food crop, где pipeline вернул не меньше ожидаемого минимального
  числа regions;
- `expected_label_recall`: доля ожидаемых категорий, совпавших с dish label полностью или как
  нормализованная подстрока;
- `confidence_coverage`: доля predictions с числовым confidence;
- `latency_ms_avg` и `latency_ms_p50`: end-to-end detector + optional crop classifier latency.

Минимальный exploratory acceptance gate:

- `multi_region_rate >= 0.625`;
- `expected_label_recall >= 0.15`;
- `confidence_coverage == 1.0`.

Низкий label threshold не является целевой product accuracy. Он нужен, чтобы baseline обнаруживал
полную деградацию label mapping; пользовательское подтверждение остаётся обязательным. Перед Beta
нужны большая лицензированная выборка, RU/EN catalog mapping, class-level precision/recall и
отдельные thresholds по типам блюд.

## Команда

```bash
python services/vision/scripts/benchmark_food_model.py \
  --validation-manifest services/vision/fixtures/validation/foodseg103_manifest.json \
  --enforce-thresholds
```

При смене checkpoint, prompt, NMS или confidence thresholds benchmark запускается повторно.

## Baseline result

Pinned pipeline проверен на восьми crop в локальном Docker container с model cache:

| Метрика | Результат |
|---|---:|
| `multi_region_rate` | `1.0` |
| `expected_label_recall` | `0.48` |
| `confidence_coverage` | `1.0` |
| `latency_ms_avg` | `14539.414` |
| `latency_ms_p50` | `12428.854` |

Exploratory acceptance gate пройден. Первый sample текущего запуска включал warm-up и занял
`28502.728 ms`; загрузка checkpoint из сети не входила в эти метрики. Предыдущий полностью cold run
с загрузкой примерно 1 GB model artifacts занял около 25 минут для первого sample, поэтому
production требует заранее полученный persistent cache и warm worker.

`multi_region_rate` измеряет число regions, а не число верно распознанных уникальных продуктов, и
может быть завышен повторными detections. `expected_label_recall=0.48` на маленькой отобранной
выборке явно недостаточен для обещаний accuracy. Baseline подтверждает работоспособность
multi-region pipeline и обнаруживает полную регрессию, но не подтверждает production-качество.

## Ограничения

- Grounding DINO возвращает bounding boxes, а не ingredient segmentation masks.
- Food-101 classifier возвращает dish-level labels и не покрывает весь каталог ингредиентов.
- Detector может вернуть ложные или повторные regions; NMS не устраняет все semantic duplicates.
- По одному RGB-фото масса не становится точной; bounding-box area не используется как
  `segment_area_px`.
- CPU inference может быть неприемлемо медленным; production sizing должен проверить GPU и более
  лёгкие detector alternatives.
- Любой результат, включая высокий confidence, остаётся proposal до подтверждения пользователя.
