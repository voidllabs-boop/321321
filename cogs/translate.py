"""
cogs/translate.py - Translation cog.

Provides prefix commands: *t, *translate, *trans, *tr, *tl
Translates text from any language to any specified target language.
Uses Google Translate via deep-translator.
"""

import logging

import disnake
from disnake.ext import commands
from deep_translator import GoogleTranslator

log = logging.getLogger("translate")

# Red accent colour — USSR | United Servers of Sovereign Republics
USSR_COLOUR = disnake.Colour(0xCC0000)

FOOTER_TEXT = "USSR | United Servers of Sovereign Republics"

# Extra aliases: Russian / common short-hand names → ISO 639-1 codes
_EXTRA_ALIASES: dict[str, str] = {
    # Russian language names
    "английский": "en",
    "русский": "ru",
    "украинский": "uk",
    "немецкий": "de",
    "французский": "fr",
    "испанский": "es",
    "итальянский": "it",
    "португальский": "pt",
    "китайский": "zh-CN",
    "японский": "ja",
    "корейский": "ko",
    "арабский": "ar",
    "турецкий": "tr",
    "польский": "pl",
    "нидерландский": "nl",
    "голландский": "nl",
    "шведский": "sv",
    "норвежский": "no",
    "датский": "da",
    "финский": "fi",
    "чешский": "cs",
    "румынский": "ro",
    "венгерский": "hu",
    "греческий": "el",
    "тайский": "th",
    "вьетнамский": "vi",
    "индонезийский": "id",
    "хинди": "hi",
    "персидский": "fa",
    "иврит": "he",
    "болгарский": "bg",
    "хорватский": "hr",
    "сербский": "sr",
    "словацкий": "sk",
    "словенский": "sl",
    "эстонский": "et",
    "латышский": "lv",
    "литовский": "lt",
    "грузинский": "ka",
    "армянский": "hy",
    "азербайджанский": "az",
    "казахский": "kk",
    "узбекский": "uz",
    "белорусский": "be",
    "албанский": "sq",
    "македонский": "mk",
    "монгольский": "mn",
    "малайский": "ms",
    "бенгальский": "bn",
    "каталанский": "ca",
    "исландский": "is",
    "ирландский": "ga",
    "валлийский": "cy",
    "суахили": "sw",
    "африкаанс": "af",
    # Common short aliases
    "eng": "en",
    "rus": "ru",
    "ukr": "uk",
    "ger": "de",
    "deu": "de",
    "fra": "fr",
    "fre": "fr",
    "spa": "es",
    "ita": "it",
    "por": "pt",
    "chi": "zh-CN",
    "chn": "zh-CN",
    "jpn": "ja",
    "jap": "ja",
    "kor": "ko",
    "ara": "ar",
    "tur": "tr",
    "pol": "pl",
    "swe": "sv",
    "nor": "no",
    "fin": "fi",
    "cze": "cs",
    "hun": "hu",
    "hin": "hi",
}

# Native display names for common languages
_LANG_DISPLAY: dict[str, str] = {
    "en": "English",
    "ru": "Русский",
    "uk": "Українська",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "pt": "Português",
    "zh-CN": "中文",
    "zh-TW": "繁體中文",
    "ja": "日本語",
    "ko": "한국어",
    "ar": "العربية",
    "tr": "Türkçe",
    "pl": "Polski",
    "nl": "Nederlands",
    "sv": "Svenska",
    "no": "Norsk",
    "da": "Dansk",
    "fi": "Suomi",
    "cs": "Čeština",
    "ro": "Română",
    "hu": "Magyar",
    "el": "Ελληνικά",
    "th": "ไทย",
    "vi": "Tiếng Việt",
    "id": "Bahasa Indonesia",
    "ms": "Bahasa Melayu",
    "hi": "हिन्दी",
    "bn": "বাংলা",
    "fa": "فارسی",
    "he": "עברית",
    "bg": "Български",
    "hr": "Hrvatski",
    "sr": "Српски",
    "sk": "Slovenčina",
    "sl": "Slovenščina",
    "et": "Eesti",
    "lv": "Latviešu",
    "lt": "Lietuvių",
    "ka": "ქართული",
    "hy": "Հայերեն",
    "az": "Azərbaycan",
    "kk": "Қазақ",
    "uz": "Oʻzbek",
    "be": "Беларуская",
    "sq": "Shqip",
    "mk": "Македонски",
    "mn": "Монгол",
    "af": "Afrikaans",
    "sw": "Kiswahili",
    "ca": "Català",
    "is": "Íslenska",
    "ga": "Gaeilge",
    "cy": "Cymraeg",
    "tl": "Tagalog",
    "mt": "Malti",
}

MAX_TRANSLATE_LEN = 5000


class TranslateCog(commands.Cog, name="Translate"):
    """Translation commands for the bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._supported: dict[str, str] = (
            GoogleTranslator().get_supported_languages(as_dict=True)
        )

    def _resolve_lang(self, raw: str) -> str | None:
        """Resolves user input (code, English name, Russian name) to an ISO code."""
        key = raw.lower().strip()

        if key in self._supported.values():
            return key

        if key in self._supported:
            return self._supported[key]

        if key in _EXTRA_ALIASES:
            return _EXTRA_ALIASES[key]

        return None

    def _lang_display(self, code: str) -> str:
        return _LANG_DISPLAY.get(code, code.upper())

    def _error_embed(self, description: str) -> disnake.Embed:
        embed = disnake.Embed(description=description, colour=USSR_COLOUR)
        embed.set_footer(text=FOOTER_TEXT)
        return embed

    @commands.command(name="t", aliases=["translate", "trans", "tr", "tl"])
    async def translate_cmd(
        self,
        ctx: commands.Context,
        lang_input: str | None = None,
        *,
        text: str | None = None,
    ):
        """
        Translate text to the specified language.

        Usage:
          *t en <text>        — translate text to English
          *t ru               — reply to a message to translate it to Russian
          *translate de Hallo — translate "Hallo" to German
        """
        if lang_input is None:
            embed = disnake.Embed(
                title="📖 Translation",
                description=(
                    "**Usage:**\n"
                    "`*t <lang> <text>` — translate text\n"
                    "`*t <lang>` — reply to a message to translate it\n\n"
                    "**Examples:**\n"
                    "`*t en Привет мир` → Hello world\n"
                    "`*t ru Hello` → Привет\n"
                    "`*translate de Good morning` → Guten Morgen\n\n"
                    "**Codes:** `en`, `ru`, `de`, `fr`, `es`, `it`, `ja`, "
                    "`ko`, `zh-CN` …\n"
                    "Full names work too: `english`, `русский`, `немецкий` …"
                ),
                colour=USSR_COLOUR,
            )
            embed.set_footer(text=FOOTER_TEXT)
            await ctx.send(embed=embed)
            return

        target = self._resolve_lang(lang_input)
        if target is None:
            await ctx.send(
                embed=self._error_embed(
                    f"❌ Unknown language: `{lang_input}`\n"
                    "Use an ISO code (`en`, `ru`, `de` …) or a full name "
                    "(`english`, `русский` …)."
                )
            )
            return

        source_text: str | None = text

        if not source_text and ctx.message.reference:
            try:
                ref = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
                source_text = ref.content
            except Exception:
                pass

        if not source_text:
            await ctx.send(
                embed=self._error_embed(
                    "❌ No text to translate.\n"
                    "Provide text after the language code or reply to a message."
                )
            )
            return

        if len(source_text) > MAX_TRANSLATE_LEN:
            source_text = source_text[:MAX_TRANSLATE_LEN]

        try:
            result = GoogleTranslator(
                source="auto", target=target
            ).translate(source_text)
        except Exception as exc:
            log.error("Translation error: %s", exc)
            await ctx.send(
                embed=self._error_embed(f"❌ Translation failed: `{exc}`")
            )
            return

        lang_name = self._lang_display(target)

        embed = disnake.Embed(description=result, colour=USSR_COLOUR)
        embed.set_author(name=f"🌐 Translation → {lang_name}")

        original_preview = (
            source_text[:1024] if len(source_text) <= 1024
            else source_text[:1021] + "…"
        )
        embed.add_field(name="Original", value=original_preview, inline=False)
        embed.add_field(
            name="Language",
            value=f"`{target}` — {lang_name}",
            inline=True,
        )
        embed.set_footer(text=FOOTER_TEXT)

        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(TranslateCog(bot))
    log.info("Translate cog loaded.")
