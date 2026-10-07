# Padrões de corte de podcast

Status: **aguardando links**. Nenhum corte foi assistido ainda. Este arquivo tem a estrutura pronta
pra ser preenchida com análise real, corte a corte. Nada aqui foi deduzido por título ou legenda.

## Por que ainda está vazio (2026-10-07)

Tentei chegar nos cortes virais pelo ambiente de nuvem e esbarrei nisto:

| Rota | Resultado |
|------|-----------|
| TikTok (site, API, espelhos) | Bloqueado pelo proxy do ambiente. Nem a página abre. |
| Instagram: busca, hashtag, perfil, aba Reels | Sem login, o Instagram devolve tela de login ou "wait a few minutes". Não dá pra listar o que viralizou. |
| Instagram: reel por link direto | **Funciona** com `yt-dlp` (baixa o vídeo, legenda do post, likes e comentários). Depois de vários testes o IP tomou 429 temporário. |
| YouTube Shorts | Bloqueado pelo proxy. A assinatura do Algrow (ferramenta de YouTube) está pausada, código 402. |
| Buscadores (Google, Bing, DDG) e portais de notícia | Bloqueados pelo proxy. A busca interna do assistente não indexa links de reels. |
| Zernio (conector) | Tem consulta pública de contas Business/Creator do Instagram (perfil + até 25 mídias recentes com likes e comentários). Recusou: sua conta @jesse.rodolfo está conectada pelo login do Instagram, e essa consulta exige conexão via **Login do Facebook**. |
| Algrow (conector) | Tem busca de virais e análise de vídeo do Instagram e TikTok. Todas as chamadas voltam 402: assinatura pausada. |

O que ficou pronto: `skill/cortes/scripts/estuda.py`. Recebe uma lista de links, baixa, transcreve
com tempo por frase, detecta trocas de plano e tira quadros (abertura em 1 fps, folha de contato,
meio e fim). Com os links na mão, a análise de 15 a 20 cortes leva menos de uma hora.

## Como destravar (escolha uma)

0. **Reconectar o Instagram no Zernio pelo Facebook.** No painel do Zernio, desconecte @jesse.rodolfo e conecte de novo escolhendo a opção Facebook. Com isso eu listo as mídias recentes de perfis de cortes (ex.: @ticaracaticastcortes), ordeno por engajamento, pego os links e assisto cada um com `estuda.py`. Cobre só Instagram e só contas Business/Creator.
0. **Reativar o Algrow.** Libera busca de virais e análise de vídeo, inclusive TikTok.
1. **Me mande os links.** Abra o Instagram e o TikTok no celular, copie o link de 15 a 20 cortes
   de podcast que viralizaram (compartilhar > copiar link) e cole aqui, um por linha. Instagram eu
   assisto daqui; TikTok só se for na opção 2.
2. **Rode no Mac**, onde o Instagram e o TikTok abrem e o `yt-dlp` pode usar o login do seu navegador:
   ```bash
   python3 ~/.claude/skills/cortes/scripts/estuda.py ~/Cortes/estudo --lista urls.txt --cookies-from-browser chrome
   ```
   Depois me passe a pasta `~/Cortes/estudo` (ou abra uma sessão local do Claude Code nela).

## Ficha por corte (uma por vídeo)

| Campo | O que registrar |
|-------|-----------------|
| Fonte | Rede, perfil, link, likes / comentários / views (quando a rede mostra) |
| Gancho (0 a 3 s) | O que aparece na tela e a **frase exata** que abre, pela transcrição |
| Tensão | Discordância, confissão, número que surpreende, opinião contra o senso comum, história com virada, outro |
| Duração e virada | Duração total; segundo em que a ideia vira (pela transcrição) |
| Legenda | Tamanho relativo, posição (terço inferior, centro...), palavra destacada (cor, caixa), palavra por palavra ou por frase |
| Ritmo de corte | Número de trocas de plano, plano médio em segundos, o que muda (câmera, zoom, b-roll, tela cheia do convidado) |
| Depois dos 10 s | O que segura: nova pergunta, lista, exemplo concreto, reação do apresentador, promessa de desfecho |
| Fim | Corte seco, conclusão fechada ou pergunta no ar; a frase final |

## Padrão (a preencher)

### Regra: apareceu na maioria dos cortes
(vazio)

### Exceção: apareceu em um ou dois
(vazio)

## Checklist pra avaliar um corte novo antes de publicar
(vazio: vem do padrão acima, não de opinião genérica)
