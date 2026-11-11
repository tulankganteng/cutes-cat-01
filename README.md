# Cutest Cat — make.fun bounty `cutest-cat-01`

A program that **draws** the cutest cat in code and writes it to
`/output/entry.png`. Python 3.13, standard library only: no Pillow, no
network, no model calls, no randomness, no clock — so both runs of the
program write byte-identical output.

## The cat

A happy ginger kitten, sitting front-on and centred on a soft cream
background, drawn with a tiny span-fill rasteriser (circles, rotated
ellipses, polygons, thick polylines and arcs) and encoded as a PNG with
`zlib`:

- head tilted, big bright amber eyes with sparkle highlights and lashes
- small pink nose, little smile with a tongue blep, pink blush, whiskers
- pink bow on one ear, tabby forehead stripes, cheek fur tufts
- curled tail with a cream tip, cream chest and paws with toe beans
- favourite toy: a red ball of yarn by its paw, with a loose strand
- a few sparkles, one tiny heart and two small flowers — nothing crowds it

One glance says cat; soft round shapes; one small story (the yarn ball);
clean storybook outlines; the cat stays clear even at ~300 px across.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png: 1024x1024 PNG, ~23 KB (limit: 1 MiB, 1024x1024)
```

Locally it runs in ~0.15 s. Two separate runs were verified to produce
byte-identical output (same sha256).

## Files

- `main.py` — the whole entry (entrypoint)
- `LICENSE` — MIT
