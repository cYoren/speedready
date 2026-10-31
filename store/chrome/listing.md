# Chrome Web Store listing

Upload: `python3 tools/build_chrome.py`, then `dist/speedready-chrome-<version>.zip`. Name and short
description come from `chrome/_locales/*/messages.json` (en, pt_BR, es, fr, de, it, nl, pl, ru, sv).
Images in this folder: `shot-*.png` (1280x800), `promo-440x280.png` (small tile), `marquee-1400x560.png`.

Category: Productivity > Education (or Tools). Language: English.
Homepage: https://speedready.vercel.app/?utm_source=chrome-store  Support: https://github.com/cYoren/speedready/issues

## Description (en)

Speedready helps you read any web page or PDF faster, right where it is. Press Alt+Shift+S (or click the toolbar button) and the article opens in a calm reader with a moving pacer that carries your eyes along the lines. Prefer one word at a time? Switch to the flash mode and set the speed.

READ FASTER
• Speed read the page you are on: the article only, without menus, ads or footers
• Select a paragraph and right-click to read just that part
• PDFs too: open a PDF in Chrome and press the button, or add your own PDF and EPUB files to your library
• Set the speed up to 1,500 words per minute, with a pacer or one word at a time

LEARN A LANGUAGE WHILE YOU READ
• Read pages in German, English, Spanish, French, Italian, Dutch, Polish, Portuguese, Russian or Swedish
• A short translation sits over each word, in your own language, so you never stop to look things up
• Mark words as known or still learning and export them to Anki
• Read aloud with the voices already on your computer

BUILD A READING HABIT
• See how many words you read today and how many days in a row you hit your goal
• Choose a daily goal of 500 to 5,000 words
• Your library remembers where you stopped in every book

PRIVATE BY DESIGN
• No account, no ads, no tracking
• The extension reads a page only when you ask it to
• Your books, words and progress stay on your computer

ALSO FROM US
Speedready is also on your phone and computer: https://speedready.vercel.app/
Datalyst tracks your habits and shows what affects your focus, sleep and mood: https://www.datalyst.one/

## Descrição (pt-BR)

O Speedready ajuda você a ler qualquer página ou PDF mais rápido, no próprio lugar. Aperte Alt+Shift+S (ou clique no botão da barra) e o artigo abre num leitor tranquilo, com um marcador que leva seus olhos pelas linhas. Prefere uma palavra por vez? Mude para o modo flash e escolha a velocidade.

LEIA MAIS RÁPIDO
• Leia rápido a página em que você está: só o artigo, sem menus, anúncios ou rodapés
• Selecione um parágrafo e clique com o botão direito para ler só aquela parte
• PDFs também: abra um PDF no Chrome e aperte o botão, ou adicione seus PDFs e EPUBs à sua biblioteca
• Até 1.500 palavras por minuto, com marcador ou uma palavra por vez

APRENDA UM IDIOMA ENQUANTO LÊ
• Leia páginas em alemão, inglês, espanhol, francês, italiano, holandês, polonês, português, russo ou sueco
• Uma tradução curta fica sobre cada palavra, no seu idioma, para você não parar para procurar
• Marque palavras como conhecidas ou em aprendizado e exporte para o Anki
• Leitura em voz alta com as vozes que já estão no seu computador

CRIE O HÁBITO DE LER
• Veja quantas palavras você leu hoje e quantos dias seguidos bateu sua meta
• Escolha uma meta diária de 500 a 5.000 palavras
• Sua biblioteca lembra onde você parou em cada livro

PRIVADO DE VERDADE
• Sem conta, sem anúncios, sem rastreamento
• A extensão só lê uma página quando você pede
• Seus livros, palavras e progresso ficam no seu computador

TAMBÉM NOSSO
O Speedready também está no seu celular e computador: https://speedready.vercel.app/
O Datalyst acompanha seus hábitos e mostra o que afeta seu foco, sono e humor: https://www.datalyst.one/

## Privacy practices tab

Single purpose: Opens the text of the current web page or PDF, or the selected text, in a speed reading view with optional word translations.

Permission `activeTab`: reads the current tab's article or selected text only after the user clicks the toolbar button, the context menu item or the keyboard shortcut.
Permission `scripting`: runs the bundled content script in that tab to collect the article text, and adds the reader frame over the page.
Permission `contextMenus`: adds "Speed read the selection" and "Speed read this page" to the right-click menu.
Permission `storage`: hands the collected text from the background script to the reader (session storage, deleted on read) and keeps the user's settings.
Remote code: No. All scripts ship inside the package. Translation dictionaries are JSON data files downloaded from https://cyoren.github.io/speedready-packs/ only when the user reads in a new language pair.
Data usage: collects no user data. Certify: not sold, not used for unrelated purposes, not used for credit decisions.
Privacy policy URL: https://speedready.vercel.app/privacy.html
