#!/usr/bin/env python3
# ruff: noqa: E501
"""Fill in missing translations across all locale files."""

import json
from pathlib import Path

LOCALES_DIR = Path("web/src/i18n/locales")

# Keys that are intentionally the same in all languages (proper nouns, abbreviations, etc.)
SKIP_SAME = {
    "app.title",
    "common.dash",
    "controls.hours24",  # "24h" is international
}

# Per-locale translations for keys that were left in English.
# Only include keys where the target language genuinely differs from English.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "de": {
        "controls.days90": "90 Tage",
        "controls.fromDate": "Von",
        "controls.toDate": "Bis",
        "controls.rangeInvalid": "Startdatum muss vor Enddatum liegen",
        "controls.granularity": "Diagrammgranularität",
        "controls.granularity_day": "Täglich",
        "controls.granularity_week": "Wöchentlich",
        "controls.granularity_month": "Monatlich",
        "chart.tokenTrend": "Token-Nutzung im Zeitverlauf",
        "chart.costTrend": "Täglicher Kostentrend",
        "chart.ioTrend": "Eingabe- vs. Ausgabe-Token",
        "chart.interactionsTrend": "Tägliche Interaktionen",
        "chart.toolShare": "Token-Anteil nach Werkzeug",
        "chart.tokensByTool": "Token nach Werkzeug (gestapelt)",
        "chart.tokensByModel": "Token nach Modell (gestapelt)",
        "chart.other": "Sonstige",
        "nav.overview": "Übersicht",
        "nav.topics": "Themen",
        "nav.sources": "Quellen",
        "nav.pricing": "Preise",
        "pages.overviewHint": "Kosten, Token-Nutzung und Werkzeuganteil auf einen Blick.",
        "pages.topicsHint": "Nach Thema, Projekt, Werkzeug oder Modell gruppieren. Auf ein Thema klicken, um detailliert anzuzeigen.",
        "pages.trendsHint": "Tägliche Token-, Kosten- und Werkzeug-/Modellverteilung im Zeitverlauf.",
        "pages.sourcesHint": "Sehen Sie, welche Werkzeug-Logs erkannt und importiert wurden.",
        "pages.topTopics": "Top-Themen nach Kosten",
    },
    "es": {
        "toolbar.error": "Error",
        "controls.days90": "90 días",
        "controls.fromDate": "Desde",
        "controls.toDate": "Hasta",
        "controls.rangeInvalid": "La fecha de inicio debe ser anterior a la fecha de fin",
        "controls.granularity": "Granularidad del gráfico",
        "controls.granularity_day": "Diario",
        "controls.granularity_week": "Semanal",
        "controls.granularity_month": "Mensual",
        "chart.tokenTrend": "Uso de tokens a lo largo del tiempo",
        "chart.costTrend": "Tendencia de costos diarios",
        "chart.ioTrend": "Tokens de entrada vs. salida",
        "chart.interactionsTrend": "Interacciones diarias",
        "chart.toolShare": "Proporción de tokens por herramienta",
        "chart.tokensByTool": "Tokens por herramienta (apilado)",
        "chart.tokensByModel": "Tokens por modelo (apilado)",
        "chart.other": "Otros",
        "nav.overview": "Resumen",
        "nav.topics": "Temas",
        "nav.sources": "Fuentes",
        "nav.pricing": "Precios",
        "pages.overviewHint": "Costos, uso de tokens y proporción de herramientas de un vistazo.",
        "pages.topicsHint": "Agrupa por tema, proyecto, herramienta o modelo. Haz clic en un tema para profundizar.",
        "pages.trendsHint": "Distribución diaria de tokens, costos y herramientas/modelos a lo largo del tiempo.",
        "pages.sourcesHint": "Ver qué registros de herramientas fueron detectados e importados.",
        "pages.topTopics": "Principales temas por costo",
    },
    "fr": {
        "stats.interactions": "Interactions",
        "controls.days90": "90 jours",
        "controls.fromDate": "De",
        "controls.toDate": "À",
        "controls.rangeInvalid": "La date de début doit être antérieure à la date de fin",
        "controls.granularity": "Granularité du graphique",
        "controls.granularity_day": "Quotidien",
        "controls.granularity_week": "Hebdomadaire",
        "controls.granularity_month": "Mensuel",
        "sources.interactions": "Interactions",
        "table.interactions": "Interactions",
        "table.source": "Source",
        "table.tokens": "Jetons",
        "chart.tokenTrend": "Utilisation des jetons au fil du temps",
        "chart.costTrend": "Tendance des coûts quotidiens",
        "chart.ioTrend": "Jetons d'entrée vs de sortie",
        "chart.interactionsTrend": "Interactions quotidiennes",
        "chart.toolShare": "Part des jetons par outil",
        "chart.tokensByTool": "Jetons par outil (empilé)",
        "chart.tokensByModel": "Jetons par modèle (empilé)",
        "chart.other": "Autre",
        "breakdown.summary": "{{interactions}} interactions · {{sessions}} sessions · {{tokens}} jetons · {{cost}}",
        "breakdown.sessions": "Sessions ({{count}})",
        "session.title": "Session",
        "common.exact": "exact",
        "nav.overview": "Vue d'ensemble",
        "nav.topics": "Sujets",
        "nav.sources": "Sources",
        "nav.pricing": "Tarification",
        "pages.overviewHint": "Coût, utilisation des jetons et part des outils en un coup d'œil.",
        "pages.topicsHint": "Regrouper par sujet, projet, outil ou modèle. Cliquez sur un sujet pour approfondir.",
        "pages.trendsHint": "Distribution quotidienne des jetons, coûts et outils/modèles au fil du temps.",
        "pages.sourcesHint": "Voir quels journaux d'outils ont été détectés et importés.",
        "pages.topTopics": "Principaux sujets par coût",
    },
    "ja": {
        "controls.days90": "90日間",
        "controls.fromDate": "開始日",
        "controls.toDate": "終了日",
        "controls.rangeInvalid": "開始日は終了日より前でなければなりません",
        "controls.granularity": "グラフの粒度",
        "controls.granularity_day": "日次",
        "controls.granularity_week": "週次",
        "controls.granularity_month": "月次",
        "chart.tokenTrend": "トークン使用量の推移",
        "chart.costTrend": "日次コストのトレンド",
        "chart.ioTrend": "入力 vs 出力トークン",
        "chart.interactionsTrend": "日次インタラクション",
        "chart.toolShare": "ツール別トークンシェア",
        "chart.tokensByTool": "ツール別トークン（積み上げ）",
        "chart.tokensByModel": "モデル別トークン（積み上げ）",
        "chart.other": "その他",
        "nav.overview": "概要",
        "nav.topics": "トピック",
        "nav.sources": "ソース",
        "nav.pricing": "料金",
        "pages.overviewHint": "コスト、トークン使用量、ツールシェアを一目で確認。",
        "pages.topicsHint": "トピック、プロジェクト、ツール、またはモデルでグループ化。トピックをクリックしてドリルダウン。",
        "pages.trendsHint": "日次トークン、コスト、ツール/モデル分布の推移。",
        "pages.sourcesHint": "どのツールログが検出・取り込まれたかを確認。",
        "pages.topTopics": "コスト上位のトピック",
    },
    "ko": {
        "controls.days90": "90일",
        "controls.fromDate": "시작일",
        "controls.toDate": "종료일",
        "controls.rangeInvalid": "시작일은 종료일 이전이어야 합니다",
        "controls.granularity": "차트 단위",
        "controls.granularity_day": "일별",
        "controls.granularity_week": "주별",
        "controls.granularity_month": "월별",
        "chart.tokenTrend": "시간별 토큰 사용량",
        "chart.costTrend": "일별 비용 추세",
        "chart.ioTrend": "입력 vs 출력 토큰",
        "chart.interactionsTrend": "일별 인터랙션",
        "chart.toolShare": "도구별 토큰 비중",
        "chart.tokensByTool": "도구별 토큰 (누적)",
        "chart.tokensByModel": "모델별 토큰 (누적)",
        "chart.other": "기타",
        "nav.overview": "개요",
        "nav.topics": "주제",
        "nav.sources": "소스",
        "nav.pricing": "가격",
        "pages.overviewHint": "비용, 토큰 사용량, 도구 비중을 한눈에 확인.",
        "pages.topicsHint": "주제, 프로젝트, 도구 또는 모델별로 그룹화. 주제를 클릭하여 세부 정보 확인.",
        "pages.trendsHint": "일별 토큰, 비용, 도구/모델 분포 추이.",
        "pages.sourcesHint": "어떤 도구 로그가 감지되고 수집되었는지 확인.",
        "pages.topTopics": "비용 상위 주제",
    },
    "tr": {
        "controls.days90": "90 gün",
        "controls.fromDate": "Başlangıç",
        "controls.toDate": "Bitiş",
        "controls.rangeInvalid": "Başlangıç tarihi bitiş tarihinden önce olmalıdır",
        "controls.granularity": "Grafik ayrıntı düzeyi",
        "controls.granularity_day": "Günlük",
        "controls.granularity_week": "Haftalık",
        "controls.granularity_month": "Aylık",
        "chart.tokenTrend": "Zaman içinde token kullanımı",
        "chart.costTrend": "Günlük maliyet trendi",
        "chart.ioTrend": "Giriş - çıkış token karşılaştırması",
        "chart.interactionsTrend": "Günlük etkileşimler",
        "chart.toolShare": "Araca göre token payı",
        "chart.tokensByTool": "Araca göre token (yığılmış)",
        "chart.tokensByModel": "Modele göre token (yığılmış)",
        "chart.other": "Diğer",
        "nav.overview": "Genel Bakış",
        "nav.topics": "Konular",
        "nav.sources": "Kaynaklar",
        "nav.pricing": "Fiyatlandırma",
        "pages.overviewHint": "Maliyet, token kullanımı ve araç payını tek bakışta görün.",
        "pages.topicsHint": "Konu, proje, araç veya modele göre gruplandırın. Konu ayrıntılarına ulaşmak için tıklayın.",
        "pages.trendsHint": "Zaman içinde günlük token, maliyet ve araç/model dağılımı.",
        "pages.sourcesHint": "Hangi araç günlüklerinin tespit edildiğini ve içe aktarıldığını görün.",
        "pages.topTopics": "Maliyete göre en iyi konular",
    },
    "uk": {
        "controls.days90": "90 днів",
        "controls.fromDate": "Від",
        "controls.toDate": "До",
        "controls.rangeInvalid": "Дата початку має бути раніше дати кінця",
        "controls.granularity": "Гранулярність графіка",
        "controls.granularity_day": "Щоденно",
        "controls.granularity_week": "Щотижня",
        "controls.granularity_month": "Щомісяця",
        "chart.tokenTrend": "Використання токенів з часом",
        "chart.costTrend": "Щоденний тренд витрат",
        "chart.ioTrend": "Вхідні проти вихідних токенів",
        "chart.interactionsTrend": "Щоденні взаємодії",
        "chart.toolShare": "Частка токенів за інструментом",
        "chart.tokensByTool": "Токени за інструментом (накопичено)",
        "chart.tokensByModel": "Токени за моделлю (накопичено)",
        "chart.other": "Інше",
        "nav.overview": "Огляд",
        "nav.topics": "Теми",
        "nav.sources": "Джерела",
        "nav.pricing": "Ціни",
        "pages.overviewHint": "Витрати, використання токенів і частка інструментів — з першого погляду.",
        "pages.topicsHint": "Групувати за темою, проектом, інструментом або моделлю. Клікніть на тему для деталей.",
        "pages.trendsHint": "Щоденний розподіл токенів, витрат та інструментів/моделей з часом.",
        "pages.sourcesHint": "Дивіться, які журнали інструментів виявлено та імпортовано.",
        "pages.topTopics": "Топ-теми за витратами",
    },
    "af": {
        "controls.days90": "90 dae",
        "controls.fromDate": "Van",
        "controls.toDate": "Tot",
        "controls.rangeInvalid": "Begindatum moet voor einddatum wees",
        "controls.granularity": "Grafiek granulariteit",
        "controls.granularity_day": "Daagliks",
        "controls.granularity_week": "Weekliks",
        "controls.granularity_month": "Maandeliks",
        "chart.tokenTrend": "Token gebruik oor tyd",
        "chart.costTrend": "Daaglikse kostetendens",
        "chart.ioTrend": "Invoer vs uitvoer tokens",
        "chart.interactionsTrend": "Daaglikse interaksies",
        "chart.toolShare": "Token aandeel per gereedskap",
        "chart.tokensByTool": "Tokens per gereedskap (gestapel)",
        "chart.tokensByModel": "Tokens per model (gestapel)",
        "chart.other": "Ander",
        "nav.overview": "Oorsig",
        "nav.topics": "Onderwerpe",
        "nav.sources": "Bronne",
        "nav.pricing": "Pryse",
        "pages.overviewHint": "Koste, token gebruik en gereedskap aandeel in een oogopslag.",
        "pages.topicsHint": "Groepeer per onderwerp, projek, gereedskap of model. Klik op 'n onderwerp om in te sny.",
        "pages.trendsHint": "Daaglikse token, koste en gereedskap/model verspreiding oor tyd.",
        "pages.sourcesHint": "Sien watter gereedskap logs bespeur en ingevoer is.",
        "pages.topTopics": "Top onderwerpe per koste",
    },
}


def set_nested(d: dict, key: str, value: str) -> None:
    """Set a dot-separated key in a nested dict."""
    parts = key.split(".", 1)
    if len(parts) == 1:
        d[key] = value
    else:
        head, tail = parts
        if head not in d:
            d[head] = {}
        set_nested(d[head], tail, value)


def apply_translations(locale: str, updates: dict[str, str]) -> int:
    path = LOCALES_DIR / f"{locale}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for key, value in updates.items():
        set_nested(data, key, value)
        count += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return count


if __name__ == "__main__":
    total = 0
    for locale, updates in TRANSLATIONS.items():
        n = apply_translations(locale, updates)
        print(f"  {locale}: applied {n} translations")
        total += n
    print(f"\nTotal: {total} translations applied across {len(TRANSLATIONS)} locales")
