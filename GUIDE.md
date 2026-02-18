Here is the consolidated **"Director's Cheat Sheet"** for your Qwen3-TTS / CosyVoice setup.

Since this model is built on CosyVoice 2/3 architecture, it understands both **Rich Text Tags** (for specific events) and **Natural Language Instructions** (for overall vibe).

You can copy-paste this entire block into a `DIRECTOR_NOTES.md` file in your project or add it to your Help tab.

---

# ???? The Director's Cheat Sheet

### 1. In-Script Action Tags (Event Triggers)

Place these *inside* your script text where you want the sound to happen.
*Note: Effectiveness depends on the model version, but `<angle_brackets>` are the standard for the Qwen/Cosy engine.*

| Action | Tag Syntax | Best Used For |
| --- | --- | --- |
| **Laughter** | `<laughter>` or `[laughter]` | Jokes, sarcasm, nervous breaks. |
| **Breathing** | `<breath>` | Exhaustion, post-sprint, panic. |
| **Sighing** | `<sigh>` | Disappointment, relief, boredom. |
| **Coughing** | `<cough>` | Sickness, clearing throat, awkwardness. |
| **Gasping** | `<gasp>` | Shock, fear, sudden realization. |
| **Giggling** | `<giggle>` | Lightheartedness, flirting, shyness. |
| **Crying** | `<cry>` | Deep sadness, breakdowns. |
| **Sniffing** | `<sniff>` | Holding back tears, cold weather. |
| **Throat Clear** | `<throat_clearing>` | Before an announcement, acting formal. |

**Experimental / Advanced Tags:**
*(These may require specific model fine-tunes but are worth trying)*

* `<whisper>` ... `<whisper/>` (Wrap text)
* `<mumble>` ... `<mumble/>`
* `<pause>` (or try `[pause]`)

---

### 2. Style Instructions (The "Vibe")

Copy these into the **"Instruction"** or **"Style"** field. These set the global tone for the generation.

#### ???? Emotional Archetypes

| Archetype | Instruction Text |
| --- | --- |
| **The Heartbroken** | "Trembling voice, holding back tears, slow pace, frequent pauses, sorrowful and broken." |
| **The Furious** | "Aggressive, shouting, very fast pace, sharp articulation, intense anger, slamming words." |
| **The Panicked** | "Breathless, fast pace, high pitch, stuttering slightly, terrified, hyperventilating." |
| **The Sarcastic** | "Bored tone, slow drawl, emphasizing the wrong words, rolling eyes, dry humor." |
| **The Overjoyed** | "Laughing voice, high energy, fast pace, smiling while speaking, ecstatic." |
| **The Seductive** | "Low pitch, breathy texture, very slow, close to microphone, intimate whisper." |
| **The Villain** | "Low, menacing whisper. Slow and calculated. Arrogant tone. Cold and gravelly." |

#### ???? Cinematic & Atmospheric

| Setting | Instruction Text |
| --- | --- |
| **Horror Narrator** | "Deep, gravelly whisper, slow and ominous, eerie pauses, threatening tone." |
| **News Anchor** | "Professional, neutral tone, clear articulation, even pacing, authoritative, no emotion." |
| **The Drunk** | "Slurred speech, uneven rhythm, fluctuating pitch, hiccuping, slow and confused." |
| **Old Radio (1950s)** | "Mid-Atlantic accent, fast pace, energetic, sharp and punchy, enthusiastic announcer." |
| **Exhausted** | "Yawning, heavy sighs, monotone, very slow, dragging words, sleepy." |
| **ASMR** | "Soft whisper, extremely close to mic, mouth sounds, slow and gentle, relaxing." |
| **Dying Breath** | "Weak, fading voice, long pauses, shallow breathing, barely audible." |

---

### 3. Confirmed Modifiers

Add these to the *end* of any instruction to tweak the delivery.

* **Distance:** `"...shouting from a distance"` / `"...far away"`
* **Proximity:** `"...close to the microphone"` / `"...intimate"`
* **Speed:** `"...speaking very fast"` / `"...extremely slow pace"`
* **Effort:** `"...while running"` / `"...out of breath"` / `"...through gritted teeth"`

---

### 4. "The Golden Rule" of Prompting

**Do not** combine conflicting instructions.

* ? **Bad:** "Shouting angrily but also whispering." (The model will hallucinate or slur).
* ? **Good:** "Angry whisper, intense and sharp." (Consistent logic).

### 5. Troubleshooting "Drunk" Artifacts

If the voice sounds slurred or glitchy:

1. **Reduce Temperature:** Drop to **0.3 - 0.5**.
2. **Simplify Instruction:** Remove complex emotions (e.g., change "sarcastically depressed" to just "sad").
3. **Check Tags:** Ensure you have spaces around your tags (e.g., `Hello <laugh> world` instead of `Hello<laugh>world`).
Here is the master **Markdown Library** of all the styles, instructions, and descriptions we used in the demo and test bench scripts.

I have formatted this so you can easily copy-paste the strings into your app code or `recipes.json` file. I�ve separated them into **Custom Voice** (Instruction-based) and **Voice Design** (Description-based).

---

# ????? Qwen3-TTS Style Library

This document contains the tested prompts used to generate the demo assets.

## 1. Emotional Archetypes

*Best used in **Custom Voice** tab with a preset speaker (e.g., Eric, Vivian).*

| Preset Name | **Instruction (Style)** | **Recommended Script Snip** |
| --- | --- | --- |
| **The Furious** | "Aggressive, shouting, very fast pace, sharp articulation, intense anger, slamming words." | "I told you to leave me alone! Get out!" |
| **The Heartbroken** | "Crying, sobbing, trembling voice, slow pace, frequent pauses, sorrowful." | "I... I just don't know what to do anymore." |
| **The Terrified** | "Breathless, fast pace, high pitch, stuttering slightly, terrified, hyperventilating." | "Did you hear that? Someone is in the house." |
| **The Ecstatic** | "Laughing voice, high energy, fast pace, smiling while speaking, ecstatic." | "Oh my god! I won! I actually won!" |
| **The Sarcastic** | "Bored tone, slow drawl, emphasizing the wrong words, rolling eyes, dry humor." | "Oh, wow. What a genius idea that was." |

---

## 2. Cinematic & Atmospheric

*Best used in **Custom Voice** to radically change the environment.*

| Preset Name | **Instruction (Style)** | **Recommended Script Snip** |
| --- | --- | --- |
| **Horror Narrator** | "Deep, gravelly whisper, slow and ominous, eerie pauses, threatening tone." | "Listen closely. I am right next to your ear." |
| **Distant Shout** | "Shouting from a long distance, loud projection, far away." | "Hey! Can you hear me over there?!" |
| **1950s Radio** | "1950s radio announcer, fast pace, energetic, Trans-Atlantic accent, sharp." | "This is the evening news, brought to you by Qwen!" |
| **The Drunk** | "Slurred speech, uneven rhythm, fluctuating pitch, hiccuping, slow and confused." | "I... I think I had too much... where are my keys?" |
| **Dying Breath** | "Weak, fading voice, long pauses, shallow breathing, barely audible." | "Tell them... I tried..." |
| **ASMR** | "Soft whisper, extremely close to microphone, mouth sounds, slow and gentle." | "Relax. Take a deep breath." |

---

## 3. Speed Modifiers

*Use these to force extreme pacing changes.*

| Preset Name | **Instruction (Style)** |
| --- | --- |
| **The Auctioneer** | "Speaking extremely fast, rapid fire, high energy, no pauses." |
| **The Slow Motion** | "Speaking very slowly, dragging every word, lethargic." |

---

## 4. Character Voices (Voice Design)

*These require the **Voice Design** tab as they define the speaker's physical identity.*

### ???? The Cowboy Narrator

* **Voice Description:** `A gritty, elderly male voice. Gravelly texture, slow pace, like a cowboy narrator.`
* **Instruction:** `Slow and gritty.`
* **Sample Text:** "You can design entirely new people just by describing them. I didn't exist until you typed this prompt."

### ??????? The Ancient Witch

* **Voice Description:** `Very old female voice, raspy, creaky texture, high pitch, cackling.`
* **Instruction:** `Sinister, slow, cackling.`
* **Sample Text:** "Add a pinch of newt, a breath of toad... yes, it is almost ready."

### ???? The Cyber-Droid

* **Voice Description:** `Neutral gender, metallic texture, flat pitch, perfectly consistent, robotic.`
* **Instruction:** `Monotone, rapid, precise.`
* **Sample Text:** "System diagnostics complete. All systems are functioning within normal parameters."

---

## 5. SFX Syntax Reference

*Tested syntax that works best with the Qwen/CosyVoice engine.*

| Sound Effect | Best Syntax | Context Prompt Required? |
| --- | --- | --- |
| **Laughter** | `[laughter]` | Yes ("Laughing, amused") |
| **Breathing** | `[breath]` | Yes ("Running, exhausted") |
| **Sighing** | `... [sigh] ...` | Yes ("Bored, tired") |
| **Throat Clear** | `[clears throat]` | Yes ("Formal, announcement") |
| **Gasping** | `[gasp]` | Yes ("Shocked, scared") |

> **Note:** Always ensure there is a space around the brackets if the effect isn't triggering (e.g., `Hello [ laughter ] world`).
Here is your master guide for **Voice Design & Direction**.

This document explains the "art" behind the controls: how to use the sliders to shape performance, and how to write prompts that actually work.

---

# ??? Qwen3-TTS: The Director?s Guide

## 1. The Precision Sliders (The "Vibe" Controls)

Think of these sliders as directing the actor's energy level. They apply to **all** tabs (Custom, Clone, and Design).

### **Temperature (Creativity & Stability)**

Controls how much "risk" the AI takes when choosing the next sound.

* **Low (0.1 ? 0.5): The "News Anchor" Zone**
* **Effect:** The voice becomes very stable, consistent, and predictable.
* **Use for:** System announcements, long technical readings, or when a Voice Clone sounds "drunk" or slurred.
* **Downside:** Can sound robotic or flat.


* **Medium (0.6 ? 0.9): The "Sweet Spot"**
* **Effect:** Natural human variation. This is the default for a reason.
* **Use for:** Most narration, podcasts, and casual speech.


* **High (1.0 ? 1.5): The "Drama" Zone**
* **Effect:** High emotion, dynamic pitch changes, and acting.
* **Use for:** Shouting, whispering, crying, or intense storytelling.
* **Downside:** High risk of artifacts (stuttering, laughing weirdly, or skipping words).



### **Top P (Vocabulary & Width)**

Controls the "range" of sounds the AI considers valid.

* **Low (0.1 ? 0.5):** Focuses on the most likely pronunciation. Good for clarity.
* **High (0.8 ? 1.0):** Allows for more diverse phrasing and intonation. Better for character acting.

---

## 2. Voice Design: The Formula

In the **Voice Design** tab, you are creating a character from scratch (Zero-Shot). The model needs two distinct pieces of information to build a person.

### **Field A: Voice Description (The "Body")**

*What does the person physically sound like?*

* **Age:** "Young child", "Mid-30s", "Elderly", "Ancient".
* **Gender:** "Male", "Female", "Androgynous".
* **Texture:** "Gravelly", "Smooth", "Raspy", "Breathy", "Nasal", "Deep", "High-pitched".
* **Accent:** "British", "Southern US", "Thick Russian accent", "Standard American".

> **Example:** *"A 60-year-old male smoker with a deep, gravelly throat and a slight cough."*

### **Field B: Style Instruction (The "Acting")**

*How are they performing right now?*

* **Pace:** "Very slow", "Fast", " conversational", "Measured".
* **Emotion:** "Sad", "Angry", "Joyful", "Neutral", "Bored".
* **Volume:** "Whispering", "Shouting", "Softly spoken", "Projecting".

> **Example:** *"Speaking slowly and quietly, as if sharing a secret. Long pauses between sentences."*

---

## 3. "Tone Recipes" (Copy-Paste Examples)

Use these combinations in the **Voice Design** tab to achieve specific results.

### **?? Emotional / Dramatic**

| Tone | Voice Description | Style Instruction |
| --- | --- | --- |
| **The Villain** | "Middle-aged male, deep baritone, smooth texture." | "Cold, menacing, slow pace. Enunciate every word clearly." |
| **Heartbroken** | "Young female, soft voice, slightly trembling." | "Sad, near tears, shaky breath. Very slow, quiet delivery." |
| **Panic/Fear** | "Androgynous voice, average pitch." | "Fast, breathless, urgent. High anxiety." |
| **The Hero** | "30s male, clear and resonant." | "Confident, inspiring, projecting authority. Energetic." |

### **?? Narrative / Professional**

| Tone | Voice Description | Style Instruction |
| --- | --- | --- |
| **Documentary** | "Older male, British accent, rich texture." | "Calm, observant, measured. Let the text breathe." |
| **Sleep Story** | "Female, mid-40s, very soft and warm." | "Whispering, extremely slow, soothing. Low energy." |
| **Sales (Hype)** | "Young adult, energetic and bright." | "Fast, punchy, smiling voice. High energy." |
| **Professor** | "Elderly female, crisp articulation." | "Formal, academic, didactic tone. Moderate pace." |

### **??? Character / Stylized**

| Tone | Voice Description | Style Instruction |
| --- | --- | --- |
| **The Monster** | "Ancient creature, extremely deep, distorted." | "Growling, slow, aggressive." |
| **The Robot** | "Neutral gender, flat pitch, no breath." | "Monotone, robotic, precise. No emotion." |
| **Old Witch** | "Very old female, raspy, creaky voice." | "Cackling, high-pitched, mischievous." |

---

## 5. Script Helper (Text Parser)

The **Script Helper** tab is a specialized tool for turning long documents into production-ready batch scripts.
*   **Automatic Splitting**: Splits long text by sentence or word count to prevent engine timeouts.
*   **Cleaning Logic**: Automatically removes square brackets `[ ]` or parentheses `( )` often found in scripts.
*   **Manual Refinement**: If a sentence is too long, the helper will prompt you to split it manually before sending it to the Batch Studio.

## 6. Modules Manager (v4.1.0)

Found as a dedicated tab in the main window, the Modules Manager is your gateway to extending the Studio.
*   **Check for new plugins**: Synchronizes with the official GitHub repository to find new creative tools.
*   **Color-Coded Status**: Green (Active), Red (Disabled), Yellow (New from current sync).
*   **Instant Toggling**: Enabling or disabling a module is applied immediately. No restart required.

## 7. Automated Scripting & Plugins
Starting in v3.6.2, Qwen3 Studio supports a dynamic plugin system. Any .py file in the ./modules/ folder can be managed via the Modules tab.
*   **Headless Automation**: Build services that watch folders or provide local APIs.
*   **Custom Tabs**: Add entirely new interfaces for specialized tasks.

## 8. Pro-Tips for Better Generation

**1. The "Pause" Trick**
The AI respects punctuation. If you want a dramatic pause, don't just write text. Use line breaks.

* Bad: "I saw him and then I ran away."
* Good:
"I saw him."
(Line Break)
"And then... I ran away."

**2. Troubleshooting "Drunk" Voices**
If a generated voice sounds slurry, garbled, or like it's dragging words:

* **Solution:** Lower the **Temperature** (try 0.4 - 0.6).
* **Solution:** Simplify the **Instruction** (remove conflicting emotions like "Happy but crying").

**3. "Locking" the Perfect Voice**
The **Voice Design** tab is random. If you generate a "Wizard" voice you absolutely love:

1. **Save the Audio:** Click "Save WAV".
2. **Move to Clone Tab:** Import that WAV as your "Source Audio".
3. **Lock It:** Use the **Lock Voice** button.
4. **Result:** Now you can generate thousands of lines with that *exact* wizard voice, using the stability of the cloning engine.
