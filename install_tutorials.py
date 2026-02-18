import os
import json
import shutil

# Define the target directory
TARGET_DIR = "tutorials"

if not os.path.exists(TARGET_DIR):
    os.makedirs(TARGET_DIR)

# --- DATA REPOSITORY ---
# This dictionary contains all filenames and their content
files = {
    # ================= ENGLISH =================
    "Tutorial_01_Welcome.json": [
        {"speaker": "Eric", "style": "News Anchor", "text": "Hi, I am Eric. I am a built-in voice, and you just generated me! Welcome to your new creative suite."},
        {"speaker": "Eric", "style": "News Anchor", "text": "Take a look at the Session History panel on the right. You will see my takes appearing there in real-time."},
        {"speaker": "Eric", "style": "News Anchor", "text": "In that history list, you can replay, delete, or even convert files to M P 3. Every line you make is automatically logged there."},
        {"speaker": "Eric", "style": "News Anchor", "text": "It's now your turn to try. Click the 'Clear All' button in the toolbar above, then load 'Tutorial_02_UI_Overview' from the tutorials folder, and click 'Run Scene' to see how to navigate the app."}
    ],
    "Tutorial_02_UI_Overview.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "Welcome to Chapter 2: The Navigation Deck. I am Ryan. Let's look at the layout of the app."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "At the very top is the Header. This is where you find the Precision Sliders. Temperature controls my creativity, while Top P controls my vocabulary breadth."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "The Stop button in the top right is your safety switch. If the engine ever feels stuck or slows down, use the 'Reset' button next to the model name to clear the memory."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Below the header are the Tabs. We have five stations: Transcript Helper, Voice Clone, Voice Design, Custom Voice, and where we are now: the Batch Studio."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Finally, look at the bottom of the window. The colored Status Bar will always tell you which engine is currently loaded and warn you if you are in the wrong tab."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "It's now your turn to try. Load 'Tutorial_03_CustomMastery' from the tutorials folder and click 'Run Scene' to explore the Custom Voice presets."}
    ],
    "Tutorial_03_CustomMastery.json": [
        {"speaker": "Vivian", "style": "News Anchor", "text": "Chapter 3: Custom Voice Mastery. I am Vivian. This tab is for fast, high-quality production using pre-trained voices like myself."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "In the Custom Voice tab, you can pick from 9 distinct identities across English, Chinese, Japanese, and Korean native accents."},
        {"speaker": "Vivian", "style": "Seductive", "text": "Performance is everything. I am now using the 'Seductive' style. You can type any acting instruction into the box to change our mood instantly."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "The 'Generate Voice Set' button is your best friend. It creates multiple emotional versions of your line so you can pick the best one."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "It's now your turn to try. Go to the 'Custom Voice' tab. Write a style description you like in the instruction field, then use the 'Save As' box to save it. We will use this in Chapter 4."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "When done, come back here, load 'Tutorial_04_VoiceDesigner' and click 'Run Scene'."}
    ],
    "Tutorial_04_VoiceDesigner.json": [
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "Welcome to the Laboratory! This is Chapter 4: Voice Design. I was created right here by a simple text description."},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "In this tab, you see two main boxes. The Description box defines the 'Body' - things like Age, Gender, and Vocal Texture."},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "The Style box defines the 'Acting'. You can even load that custom style you saved in Chapter 3 right here!"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "It's now your turn to try. Go to the 'Voice Design' tab. In the description box, type: 'A futuristic A I assistant voice, neutral and crisp'. In the target text box, type: 'Engine Loaded', and click 'Generate Design'."},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "Next, go to your Session History. Right-click your new take and select 'Set as Notification Sound'. This makes your creation the app's ready sound!"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "Finally, create one more character you love, generate a line, and click 'Save WAV' in the history. We will clone that file in Chapter 5. Load it when you are ready."}
    ],
    "Tutorial_05_Cloning.json": [
        {"speaker": "Aiden", "style": "News Anchor", "text": "Chapter 5: Voice Cloning. I am Aiden. This is the Purple engine, used for creating perfect digital replicas of any person."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "For a good clone, you need clean audio. You can prepare these in the 'Transcript Helper' tab, which includes a recorder and a manual cropping tool."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "In the Clone tab, you can use 'Ignore Text' mode for a quick acoustic match, but providing a transcript always gives you much higher accuracy."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Use the 'Lock Voice' button to cache the speaker's data so you can generate thousands of lines without any extra loading time."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "It's now your turn to try. Go to the 'Voice Clone' tab. Load the character WAV you saved in the previous chapter. Type some text, use the 'Lock Voice' button, and generate your first clone."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "When you are done, come back to the Studio, load 'Tutorial_06_BatchStudio' and click 'Run Scene' for the grand finale."}
    ],
    "Tutorial_06_BatchStudio.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "Finale: Chapter 6. The Batch Studio. This is where all the engines meet. You are currently looking at the editor interface."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Observe the toolbar above. You can Save and Load your scripts, and even see the name of your current project next to the page icon."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "On the far right is the Style Manager. You can create new acting instructions here and they will instantly appear in all your script blocks."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "The Review system is key. Yellow blocks are fresh takes. Click to approve them (Green) or right-click to reject them (Red) for a retry."},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "It's now your turn to try. Tick the 'Auto-Switch' box at the bottom and click 'RUN SCENE'. The app will automatically swap models and play your whole scene when finished!"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "You've mastered the main stage! But we aren't done yet. Load Chapter 7 to learn about the 'Prep Station' and automatic transcription."}
    ],
    "Tutorial_07_PrepStation.json": [
        {"speaker": "Aiden", "style": "News Anchor", "text": "Welcome to Chapter 7: The Prep Station. This is the 'Transcript Helper' tab, where you capture and clean your reference data."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "The Workbench features a recorder that supports both your Microphone and System Audio via the 'Sys Audio' loopback checkbox."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "It's now your turn to try. Go to the 'Transcript Helper'. Click the 'Audio to Text' button. The app will use the Whisper engine to listen to your file and write the script for you!"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "Need to clean up a recording? Left-click the waveform for the start and Right-click for the end, then click 'Crop'. It's that simple."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Finally, give your voice a name in the Profile box and click 'Save'. This creates a permanent Studio Profile that you can load anywhere in the app."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "When you are ready, load the final chapter, Chapter 8, to learn the pro techniques for high-end production."}
    ],
    "Tutorial_08_AdvancedMastery.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "Chapter 8: Pro-Level Production. Let's talk about the small details that make a big difference."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "Did you know you can trigger human sounds? Try adding [ laughter ] or [ breath ] inside your text. Just remember to put spaces around the brackets!"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "If a generation is too quiet, find it in the History panel, right-click, and select 'Normalize'. This will boost the volume to a professional level automatically."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "Help the app learn your computer's speed. After a successful generation, click the 'Log' button in the header. The app will start predicting how long each line will take to finish."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Need to move your files? Click the Gear icon in the top right to change your SoX or Engine paths without reinstalling anything."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "It's now your turn to try. Experiment with action tags and sliders to find your unique sound. You are now a master of the Qwen 3 T T S Pro Suite. Happy directing!"}
    ],

    # ================= SPANISH =================
    "Tutorial_01_Welcome_ES.json": [
        {"speaker": "Eric", "style": "News Anchor", "text": "Hola, soy Eric. Soy una voz integrada, ¡y acabas de generarme! Bienvenido a tu nueva suite creativa."},
        {"speaker": "Eric", "style": "News Anchor", "text": "Echa un vistazo al panel Session History a la derecha. Verás mis tomas apareciendo allí en tiempo real."},
        {"speaker": "Eric", "style": "News Anchor", "text": "En esa lista del history, puedes reproducir, eliminar o incluso convertir archivos a MP3. Cada línea que haces se registra automáticamente allí."},
        {"speaker": "Eric", "style": "News Anchor", "text": "Ahora es tu turno de probar. Haz clic en el botón 'Clear All' en la barra de herramientas superior, luego carga 'Tutorial_02_UI_Overview' desde la carpeta de tutoriales y haz clic en 'Run Scene' para ver cómo navegar por la aplicación."}
    ],
    "Tutorial_02_UI_Overview_ES.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "Bienvenido al Capítulo 2: El Panel de Navegación. Soy Ryan. Veamos el diseño de la aplicación."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "En la parte superior está el Header. Aquí es donde encuentras los Precision Sliders. Temperature controla mi creatividad, mientras que Top P controla la amplitud de mi vocabulario."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "El botón Stop arriba a la derecha es tu interruptor de seguridad. Si el motor parece atascado o lento, usa el botón 'Reset' junto al nombre del modelo para limpiar la memoria."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Debajo del encabezado están las Tabs. Tenemos cinco estaciones: Transcript Helper, Voice Clone, Voice Design, Custom Voice, y donde estamos ahora: el Batch Studio."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Finalmente, mira la parte inferior de la ventana. La Status Bar de color siempre te dirá qué motor está cargado y te avisará si estás en la pestaña incorrecta."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Ahora es tu turno. Carga 'Tutorial_03_CustomMastery' y haz clic en 'Run Scene' para explorar los ajustes preestablecidos de Custom Voice."}
    ],
    "Tutorial_03_CustomMastery_ES.json": [
        {"speaker": "Vivian", "style": "News Anchor", "text": "Capítulo 3: Maestría en Custom Voice. Soy Vivian. Esta pestaña es para producción rápida y de alta calidad usando voces preentrenadas como yo."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "En la pestaña Custom Voice, puedes elegir entre 9 identidades distintas con acentos nativos en inglés, chino, japonés y coreano."},
        {"speaker": "Vivian", "style": "Seductive", "text": "La actuación lo es todo. Ahora estoy usando el estilo 'Seductive'. Puedes escribir cualquier instrucción de actuación en el cuadro para cambiar nuestro estado de ánimo al instante."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "El botón 'Generate Voice Set' es tu mejor amigo. Crea múltiples versiones emocionales de tu línea para que puedas elegir la mejor."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "Ahora es tu turno. Ve a la pestaña 'Custom Voice'. Escribe una descripción de estilo que te guste en el campo de instrucción, luego usa el cuadro 'Save As' para guardarlo. Usaremos esto en el Capítulo 4."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "Cuando termines, vuelve aquí, carga 'Tutorial_04_VoiceDesigner' y haz clic en 'Run Scene'."}
    ],
    "Tutorial_04_VoiceDesigner_ES.json": [
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "¡Bienvenido al Laboratorio! Este es el Capítulo 4: Voice Design. Fui creado justo aquí mediante una simple descripción de texto."},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "En esta pestaña, ves dos cuadros principales. El cuadro Description define el 'Cuerpo' - cosas como Edad, Género y Textura Vocal."},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "El cuadro Style define la 'Actuación'. ¡Incluso puedes cargar ese estilo personalizado que guardaste en el Capítulo 3 justo aquí!"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "Ahora es tu turno. Ve a la pestaña 'Voice Design'. En el cuadro de descripción, escribe: 'A futuristic AI assistant voice, neutral and crisp'. En el cuadro de texto objetivo, escribe: 'Engine Loaded', y haz clic en 'Generate Design'."},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "Luego, ve a tu Session History. Haz clic derecho en tu nueva toma y selecciona 'Set as Notification Sound'. ¡Esto convierte tu creación en el sonido de listo de la aplicación!"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "Finalmente, crea un personaje más que te encante, genera una línea y haz clic en 'Save WAV' en el historial. Clonaremos ese archivo en el Capítulo 5. Cárgalo cuando estés listo."}
    ],
    "Tutorial_05_Cloning_ES.json": [
        {"speaker": "Aiden", "style": "News Anchor", "text": "Capítulo 5: Voice Cloning. Soy Aiden. Este es el motor Púrpura, usado para crear réplicas digitales perfectas de cualquier persona."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Para un buen clon, necesitas audio limpio. Puedes prepararlos en la pestaña 'Transcript Helper', que incluye una grabadora y una herramienta de recorte manual."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "En la pestaña Clone, puedes usar el modo 'Ignore Text' para una coincidencia acústica rápida, pero proporcionar una transcripción siempre te da una precisión mucho mayor."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Usa el botón 'Lock Voice' para guardar en caché los datos del hablante y así poder generar miles de líneas sin tiempo de carga extra."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Ahora es tu turno. Ve a la pestaña 'Voice Clone'. Carga el WAV del personaje que guardaste en el capítulo anterior. Escribe algo de texto, usa el botón 'Lock Voice' y genera tu primer clon."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Cuando termines, vuelve al Studio, carga 'Tutorial_06_BatchStudio' y haz clic en 'Run Scene' para el gran final."}
    ],
    "Tutorial_06_BatchStudio_ES.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "Final: Capítulo 6. El Batch Studio. Aquí es donde se encuentran todos los motores. Actualmente estás viendo la interfaz del editor."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Observa la barra de herramientas arriba. Puedes usar Save y Load para tus guiones, e incluso ver el nombre de tu proyecto actual junto al icono de página."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "En el extremo derecho está el Style Manager. Puedes crear nuevas instrucciones de actuación aquí y aparecerán instantáneamente en todos tus bloques de guion."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "El sistema de Review es clave. Los bloques amarillos son tomas nuevas. Haz clic para aprobarlas (Verde) o clic derecho para rechazarlas (Rojo) y reintentar."},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "Ahora es tu turno. Marca la casilla 'Auto-Switch' en la parte inferior y haz clic en 'RUN SCENE'. La aplicación cambiará automáticamente los modelos y reproducirá toda tu escena cuando termine!"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "¡Has dominado el escenario principal! Pero aún no hemos terminado. Carga el Capítulo 7 para aprender sobre la 'Prep Station' y la transcripción automática."}
    ],
    "Tutorial_07_PrepStation_ES.json": [
        {"speaker": "Aiden", "style": "News Anchor", "text": "Bienvenido al Capítulo 7: La Prep Station. Esta es la pestaña 'Transcript Helper', donde capturas y limpias tus datos de referencia."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "El Workbench cuenta con una grabadora que soporta tanto tu Micrófono como el Audio del Sistema a través de la casilla 'Sys Audio'."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Ahora es tu turno. Ve al 'Transcript Helper'. Haz clic en el botón 'Audio to Text'. ¡La aplicación usará el motor Whisper para escuchar tu archivo y escribir el guion por ti!"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "¿Necesitas limpiar una grabación? Haz clic izquierdo en la onda para el inicio y clic derecho para el final, luego haz clic en 'Crop'. Es así de simple."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Finalmente, dale un nombre a tu voz en el cuadro Profile y haz clic en 'Save'. Esto crea un perfil de estudio permanente que puedes cargar en cualquier parte de la aplicación."},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Cuando estés listo, carga el capítulo final, Capítulo 8, para aprender las técnicas pro para producción de alta gama."}
    ],
    "Tutorial_08_AdvancedMastery_ES.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "Capítulo 8: Producción Nivel Pro. Hablemos de los pequeños detalles que marcan una gran diferencia."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "¿Sabías que puedes activar sonidos humanos? Intenta agregar [ laughter ] o [ breath ] dentro de tu texto. ¡Solo recuerda poner espacios alrededor de los corchetes!"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Si una generación es demasiado silenciosa, búscala en el panel History, haz clic derecho y selecciona 'Normalize'. Esto aumentará el volumen a un nivel profesional automáticamente."},
        {"speaker": "Vivian", "style": "News Anchor", "text": "Ayuda a la aplicación a aprender la velocidad de tu computadora. Después de una generación exitosa, haz clic en el botón 'Log' en el encabezado. La aplicación comenzará a predecir cuánto tardará cada línea en terminar."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "¿Necesitas mover tus archivos? Haz clic en el icono de engranaje arriba a la derecha para cambiar tus rutas de SoX o Engine sin reinstalar nada."},
        {"speaker": "Ryan", "style": "News Anchor", "text": "Ahora es tu turno de experimentar. Juega con las etiquetas de acción y los controles deslizantes para encontrar tu sonido único. Ahora eres un maestro de Qwen 3 T T S Pro Suite. ¡Feliz dirección!"}
    ],

    # ================= CHINESE =================
    "Tutorial_01_Welcome_CN.json": [
        {"speaker": "Eric", "style": "News Anchor", "text": "嗨，我是 Eric。我是内置语音，你刚刚生成了我！欢迎使用你的新创意套件。"},
        {"speaker": "Eric", "style": "News Anchor", "text": "看看右边的 Session History 面板。你会看到我的录音实时出现在那里。"},
        {"speaker": "Eric", "style": "News Anchor", "text": "在这个 history 列表中，你可以重播、删除，甚至将文件转换为 MP3。你制作的每一行都会自动记录在那里。"},
        {"speaker": "Eric", "style": "News Anchor", "text": "现在轮到你尝试了。点击上方工具栏中的 'Clear All' 按钮，然后从教程文件夹加载 'Tutorial_02_UI_Overview'，并点击 'Run Scene' 看看如何导航应用。"}
    ],
    "Tutorial_02_UI_Overview_CN.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "欢迎来到第2章：导航面板。我是 Ryan。让我们看看应用的布局。"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "最顶部是 Header。在这里你可以找到 Precision Sliders。Temperature 控制我的创造力，而 Top P 控制我的词汇广度。"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "右上角的 Stop 按钮是你的安全开关。如果引擎感觉卡住或变慢，请使用模型名称旁边的 'Reset' 按钮清除内存。"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "在标题下方是 Tabs。我们有五个工作站：Transcript Helper、Voice Clone、Voice Design、Custom Voice，以及我们现在所在的：Batch Studio。"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "最后，看窗口底部。彩色的 Status Bar 总是会告诉你当前加载了哪个引擎，并会在你处于错误的标签页时警告你。"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "现在轮到你尝试了。加载 'Tutorial_03_CustomMastery' 并点击 'Run Scene' 来探索 Custom Voice 预设。"}
    ],
    "Tutorial_03_CustomMastery_CN.json": [
        {"speaker": "Vivian", "style": "News Anchor", "text": "第3章：精通 Custom Voice。我是 Vivian。这个标签页用于使用像我这样的预训练语音进行快速、高质量的制作。"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "在 Custom Voice 标签页中，你可以从9个不同的身份中进行选择，涵盖英语、中文、日语和韩语的母语口音。"},
        {"speaker": "Vivian", "style": "Seductive", "text": "表演就是一切。我现在使用的是 'Seductive' 风格。你可以在框中输入任何表演指令来立即改变我们的情绪。"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "'Generate Voice Set' 按钮是你最好的朋友。它会为你的一行台词创建多个情感版本，以便你选择最好的一个。"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "现在轮到你尝试了。去 'Custom Voice' 标签页。在指令字段中写下你喜欢的风格描述，然后使用 'Save As' 框保存它。我们将在第4章中使用这个。"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "完成后，回到这里，加载 'Tutorial_04_VoiceDesigner' 并点击 'Run Scene'。"}
    ],
    "Tutorial_04_VoiceDesigner_CN.json": [
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "欢迎来到实验室！这是第4章：Voice Design。我就是在这里通过简单的文字描述被创造出来的。"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "在这个标签页中，你看到两个主要框。Description 框定义了 '身体' —— 比如年龄、性别和声音质感。"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "Style 框定义了 '表演'。你甚至可以在这里加载你在第3章中保存的那个自定义风格！"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "现在轮到你尝试了。去 'Voice Design' 标签页。在描述框中输入：'A futuristic AI assistant voice, neutral and crisp'。在目标文本框中输入：'Engine Loaded'，然后点击 'Generate Design'。"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "接下来，去你的 Session History。右键点击你的新录音并选择 'Set as Notification Sound'。这会把你的作品变成应用的就绪提示音！"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "最后，再创建一个你喜欢的角色，生成一行台词，然后在历史记录中点击 'Save WAV'。我们将在第5章克隆那个文件。准备好后加载它。"}
    ],
    "Tutorial_05_Cloning_CN.json": [
        {"speaker": "Aiden", "style": "News Anchor", "text": "第5章：Voice Cloning。我是 Aiden。这是紫色引擎，用于创建任何人的完美数字复制品。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "为了获得好的克隆，你需要干净的音频。你可以在 'Transcript Helper' 标签页中准备这些，那里包含录音机和手动裁剪工具。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "在 Clone 标签页中，你可以使用 'Ignore Text' 模式进行快速声学匹配，但提供文本记录总是能给你更高的准确性。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "使用 'Lock Voice' 按钮缓存说话者的数据，这样你就可以生成数千行台词而无需额外的加载时间。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "现在轮到你尝试了。去 'Voice Clone' 标签页。加载你在上一章保存的角色 WAV 文件。输入一些文本，使用 'Lock Voice' 按钮，并生成你的第一个克隆。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "完成后，回到 Studio，加载 'Tutorial_06_BatchStudio' 并点击 'Run Scene' 观看大结局。"}
    ],
    "Tutorial_06_BatchStudio_CN.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "终章：第6章。Batch Studio。这是所有引擎汇聚的地方。你现在看到的是编辑器界面。"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "观察上方的工具栏。你可以使用 Save 和 Load 来管理你的剧本，甚至可以在页面图标旁边看到当前项目的名称。"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "最右边是 Style Manager。你可以在这里创建新的表演指令，它们会立即出现在你所有的剧本块中。"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "Review 系统是关键。黄色块是新生成的。点击批准（绿色）或右键点击拒绝（红色）并重试。"},
        {"speaker": "Tutorial Wizard", "style": "News Anchor", "text": "现在轮到你尝试了。勾选底部的 'Auto-Switch' 框，然后点击 'RUN SCENE'。应用会自动切换模型并在完成后播放你的整个场景！"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "你已经掌握了主舞台！但我们还没结束。加载第7章以了解 'Prep Station' 和自动转录。"}
    ],
    "Tutorial_07_PrepStation_CN.json": [
        {"speaker": "Aiden", "style": "News Anchor", "text": "欢迎来到第7章：Prep Station。这是 'Transcript Helper' 标签页，你在那里捕获和清理参考数据。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "Workbench 具有录音功能，支持通过 'Sys Audio' 复选框同时录制你的麦克风和系统音频。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "现在轮到你尝试了。去 'Transcript Helper'。点击 'Audio to Text' 按钮。应用将使用 Whisper 引擎听你的文件并为你写出剧本！"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "需要清理录音吗？左键点击波形设置起点，右键点击设置终点，然后点击 'Crop'。就是这么简单。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "最后，在 Profile 框中给你的声音起个名字并点击 'Save'。这会创建一个永久的工作室配置文件，你可以在应用的任何地方加载它。"},
        {"speaker": "Aiden", "style": "News Anchor", "text": "当你准备好后，加载最后一章，第8章，学习高端制作的专业技巧。"}
    ],
    "Tutorial_08_AdvancedMastery_CN.json": [
        {"speaker": "Ryan", "style": "News Anchor", "text": "第8章：专业级制作。让我们谈谈那些能带来巨大差异的小细节。"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "你知道你可以触发人类声音吗？尝试在文本中添加 [ laughter ] 或 [ breath ]。只要记得在括号周围加上空格！"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "如果生成的音频太安静，请在 History 面板中找到它，右键点击并选择 'Normalize'。这会自动将音量提升到专业水平。"},
        {"speaker": "Vivian", "style": "News Anchor", "text": "帮助应用学习你电脑的速度。生成成功后，点击标题栏中的 'Log' 按钮。应用将开始预测每行台词完成所需的时间。"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "需要移动文件吗？点击右上角的齿轮图标更改你的 SoX 或 Engine 路径，无需重新安装任何东西。"},
        {"speaker": "Ryan", "style": "News Anchor", "text": "现在轮到你实验了。使用动作标签和滑块来找到你独特的声音。你现在是 Qwen 3 T T S Pro Suite 的大师了。祝你导演愉快！"}
    ]
}

# Write files to disk
print(f"Installing {len(files)} tutorial scripts into '{TARGET_DIR}'...")

for filename, content in files.items():
    path = os.path.join(TARGET_DIR, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=4, ensure_ascii=False)
        print(f"✅ Created: {filename}")
    except Exception as e:
        print(f"❌ Error creating {filename}: {e}")

print("\nInstallation complete. You can now load these files in the Batch Studio.")