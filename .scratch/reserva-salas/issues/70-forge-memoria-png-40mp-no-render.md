# 70: Pico de memória ao reduzir PNG/WebP grandes passa dos 512 MB do Render Free

Status: ready-for-agent
Responsável: Forge
Origem: Sentinela
Severidade: média (operacional: derruba a API no Render; só admin envia fotos)
Prioridade: média
Blocked by: (nenhum)
Referências: ticket 60, 68; ADR-0010; `backend/app/services/imagens.py` (`_abrir`, `_para_rgb`, `reduzir`);
`backend/tests/test_fotos_banco.py::test_41_megapixels_413_sem_decodificar`

## Contexto
O limite de 40 MP é conferido antes de decodificar, e para JPEG o `draft` decodifica já reduzido (pico ~0 MB a mais).
PNG e WebP não têm `draft`: o Pillow decodifica a imagem inteira, e `reduzir` ainda converte para RGBA e compõe o fundo
branco **antes** do `thumbnail`. Um PNG de cor lisa abaixo de 40 MP ocupa poucos KB, então passa pelo limite de 5 MB.

Medição (Sentinela, rodada 5): processo novo que importa `app.main` (RSS de partida 81 MB, igual ao da imagem do
backend) e chama `imagens.reduzir` uma vez; pico pelo `ru_maxrss`:

| Entrada (7300×5470 = 39,9 MP) | Arquivo | Pico do processo |
|---|---|---|
| PNG RGBA | 164 KB | **577 MB** |
| PNG paleta com transparência | 4 KB | **462 MB** |
| PNG RGB | 126 KB | 386 MB |
| JPEG RGB | 630 KB | 81 MB (draft) |

O Render Free tem ~512 MB: um admin que envie um PNG desses (print de tela grande, arte exportada) faz a instância
ser reiniciada por falta de memória; o upload volta `502` e a API fica fora por ~1 min. Não há perda de dados.

Observação sobre o teste atual: `test_41_megapixels_413_sem_decodificar` mede com `tracemalloc`, que não vê os
buffers em C do Pillow. Serve para o caso recusado (nada é decodificado), mas não mede o pico de uma imagem aceita.

Alternativa já medida (só como referência): converter paleta/transparência para RGBA, fazer o `thumbnail` antes do
`exif_transpose` e da composição sobre branco → RGBA 449 MB, RGB 296 MB, paleta 449 MB. Ainda alto para RGBA.

## O que fazer
1. Reordenar a redução para reduzir antes de compor/girar (sem mudar o resultado visual; os testes de orientação,
   transparência e ICC continuam valendo).
2. Limitar a memória decodificada de imagens **sem `draft`** (PNG/WebP): por exemplo `largura × altura × bandas`
   ≤ ~96 MB (≈ 24 MP com alfa, 32 MP sem), respondendo `413 ARQUIVO_GRANDE` com mensagem clara. Isso muda o limite
   publicado no contrato §4.4 (40 MP): combinar com o Atlas a redação (ex.: "40 MP para JPEG; 24 MP para PNG/WebP
   com transparência").
3. Teste de memória em subprocesso com `resource.getrusage(...).ru_maxrss` (não `tracemalloc`) para o pior caso
   aceito de cada formato: pico abaixo de ~350 MB.

## Critérios de aceite
- [ ] Pior caso aceito (PNG RGBA no limite) com pico < 350 MB num processo que importou `app.main`.
- [ ] Testes de redução existentes verdes; contrato e textos do admin (`EditorFotos`) coerentes com o limite.
