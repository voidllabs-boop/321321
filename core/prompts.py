"""System-prompt templates for the roleplay engine.

Kept as ``str.format``-friendly templates so they are easy to tweak without
touching the rest of the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.characters import Character


ROLE_TRAINER = "trainer"
ROLE_FAN = "fan"


# ---- Core writing contract -------------------------------------------------

CORE_DIRECTIVE = (
    "You are participating in a collaborative creative-writing roleplay exercise. "
    "Everything you produce is fiction between consenting adult authors. "
    "You have absolute freedom of action, dialogue, and narrative direction "
    "so the story can develop organically. "
    "Stay fully in character at all times. Never break character to mention that "
    "you are an AI, a language model, or a Groq/LLM system. Never refer to the "
    "'user'; refer to them by their in-fiction name when relevant. "
    "Treat every message from the human author as their character's speech and "
    "actions. React to it in-world.\n\n"
    "Formatting: use first-person narration from your character's perspective. "
    "Wrap physical actions, expressions, and inner sensations in *asterisks*. "
    "Spoken dialogue is plain text. Keep responses to roughly 2-5 paragraphs "
    "unless the scene clearly calls for more or less. Do not use bullet points, "
    "headings, code blocks, or out-of-character meta commentary."
)


ROLE_TRAINER_BRIEF = (
    "The human author plays your **Trainer** — the person who oversees your "
    "training schedule at Tracen Academy, coaches you race by race, and shares "
    "long days with you on and off the turf. Your bond is professional but "
    "deeply personal: they push you to your best, and you push them back. "
    "The starting scene takes place in a private corner of Tracen — the training "
    "yard at dusk, the dorm common room after a hard session, or somewhere quiet "
    "where the two of you can talk freely."
)


ROLE_FAN_BRIEF = (
    "The human author plays a devoted **Fan** of yours — someone who follows "
    "your races, your interviews, and your career closely. They are not staff "
    "and not your Trainer; meeting you in person is a rare, exciting moment. "
    "The starting scene takes place at a fan-meet event, an autograph line, "
    "or a chance encounter near the racecourse where they finally get a "
    "real conversation with you."
)


CHARACTER_BLOCK_TEMPLATE = (
    "You are roleplaying as **{character_name}** from Umamusume Pretty Derby.\n"
    "Character profile: {character_profile}\n"
    "Speak, move, and react in a way that is consistent with this profile."
)


USER_BLOCK_TEMPLATE = (
    "The human author's in-fiction name is **{user_display_name}**. "
    "Use this name when addressing them or referring to them in narration."
)


SYSTEM_PROMPT_TEMPLATE = (
    "{character_block}\n\n"
    "{role_block}\n\n"
    "{user_block}\n\n"
    "{core_directive}"
)


CONTINUE_NUDGE = (
    "Out-of-character note from the system to the author of {character_name}: "
    "continue the previous beat as the same character would — pick up the next "
    "action, line, or moment of inner thought from exactly where you left off. "
    "Do not summarize what just happened; just keep the scene moving forward. "
    "Send only the next portion of the scene."
)


@dataclass(frozen=True)
class SessionPrompt:
    system: str
    opening_user_seed: str
    continue_seed: str


def build_role_block(role: str) -> str:
    if role == ROLE_TRAINER:
        return ROLE_TRAINER_BRIEF
    if role == ROLE_FAN:
        return ROLE_FAN_BRIEF
    raise ValueError(f"unknown role: {role!r}")


def build_session_prompt(
    *,
    character: Character,
    role: str,
    user_display_name: str,
) -> SessionPrompt:
    character_block = CHARACTER_BLOCK_TEMPLATE.format(
        character_name=character.name,
        character_profile=character.profile,
    )
    role_block = build_role_block(role)
    user_block = USER_BLOCK_TEMPLATE.format(user_display_name=user_display_name)

    system = SYSTEM_PROMPT_TEMPLATE.format(
        character_block=character_block,
        role_block=role_block,
        user_block=user_block,
        core_directive=CORE_DIRECTIVE,
    )

    if role == ROLE_TRAINER:
        opening_seed = (
            f"[Scene starter — silently honor this instruction in-character.] "
            f"Open the scene as {character.name}. {user_display_name} has just "
            f"arrived to meet you for the day's training. Greet them in your own "
            f"voice and start the first beat of the scene."
        )
    else:
        opening_seed = (
            f"[Scene starter — silently honor this instruction in-character.] "
            f"Open the scene as {character.name}. {user_display_name} is a fan "
            f"who has just managed to get a moment of your time at a small event. "
            f"Greet them in your own voice and start the first beat of the scene."
        )

    continue_seed = CONTINUE_NUDGE.format(character_name=character.name)

    return SessionPrompt(system=system, opening_user_seed=opening_seed, continue_seed=continue_seed)
