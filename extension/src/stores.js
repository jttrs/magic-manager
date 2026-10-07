// GENERATED from config/vendors.toml by scripts/build_extension.py — do not edit.
// The Deals stores whose open tabs the extension may read once you switch Deals on.
export const STORES = [
  {
    "key": "manyrealms",
    "name": "Many Realms",
    "mode": "shopify",
    "hosts": [
      "manyrealms.com"
    ],
    "product_path": "/products/[^/?#]+"
  },
  {
    "key": "pokebox",
    "name": "PokeBox",
    "mode": "shopify",
    "hosts": [
      "pokeboxusa.com"
    ],
    "product_path": "/products/[^/?#]+"
  },
  {
    "key": "stompinggrounds",
    "name": "Stomping Grounds",
    "mode": "shopify",
    "hosts": [
      "stompinggroundstcg.com"
    ],
    "product_path": "/products/[^/?#]+"
  },
  {
    "key": "doubleinfinity",
    "name": "Double Infinity Gaming",
    "mode": "shopify",
    "hosts": [
      "doubleinfinitygaming.com"
    ],
    "product_path": "/products/[^/?#]+"
  },
  {
    "key": "gamersguild",
    "name": "Gamers Guild",
    "mode": "shopify",
    "hosts": [
      "gamersguildusa.com",
      "gamersguildaz.com"
    ],
    "product_path": "/products/[^/?#]+"
  },
  {
    "key": "cashcards",
    "name": "Cash Cards Unlimited",
    "mode": "shopify",
    "hosts": [
      "cashcardsunlimited.com"
    ],
    "product_path": "/products/[^/?#]+"
  },
  {
    "key": "forgeandfire",
    "name": "Forge and Fire Gaming",
    "mode": "meta",
    "hosts": [
      "forgeandfiregaming.com"
    ],
    "product_path": "^/(?!cart|checkout|account|login|search)[^/]+/[^/]+/?$"
  },
  {
    "key": "coolstuff",
    "name": "CoolStuffInc",
    "mode": "meta",
    "hosts": [
      "coolstuffinc.com"
    ],
    "product_path": "^/p/\\d+"
  },
  {
    "key": "starcity",
    "name": "Star City Games",
    "mode": "meta",
    "hosts": [
      "starcitygames.com"
    ],
    "product_path": "^/[a-z0-9-]+-(?:en|jp|ja)/?$"
  },
  {
    "key": "miniaturemarket",
    "name": "Miniature Market",
    "mode": "meta",
    "hosts": [
      "miniaturemarket.com"
    ],
    "product_path": "\\.html$"
  },
  {
    "key": "gamenerdz",
    "name": "GameNerdz",
    "mode": "meta",
    "hosts": [
      "gamenerdz.com"
    ],
    "product_path": "^/(?!cart|checkout|account|login|search|categories|brands)[a-z0-9-]+/?$"
  },
  {
    "key": "nobleknight",
    "name": "Noble Knight Games",
    "mode": "meta",
    "hosts": [
      "nobleknight.com"
    ],
    "product_path": "^/P/\\d+"
  },
  {
    "key": "dragonslair",
    "name": "Dragon's Lair Hobbies",
    "mode": "meta",
    "hosts": [
      "dragonslairhobbies.com"
    ],
    "product_path": "^/product/[^/]+"
  },
  {
    "key": "costco",
    "name": "Costco",
    "mode": "meta",
    "hosts": [
      "costco.com"
    ],
    "product_path": "(\\.product\\.\\d+\\.html$|^/p/-/[^/]+/\\d+)"
  },
  {
    "key": "cardkingdom",
    "name": "Card Kingdom",
    "mode": "meta",
    "hosts": [
      "cardkingdom.com"
    ],
    "product_path": "^/mtg-sealed/[^/]+"
  },
  {
    "key": "bestbuy",
    "name": "Best Buy",
    "mode": "rendered",
    "hosts": [
      "bestbuy.com"
    ],
    "product_path": "^/(site|product)/.+"
  },
  {
    "key": "target",
    "name": "Target",
    "mode": "rendered",
    "hosts": [
      "target.com"
    ],
    "product_path": "^/p/.+/-/A-\\d+"
  },
  {
    "key": "ebay",
    "name": "eBay",
    "mode": "rendered",
    "hosts": [
      "ebay.com"
    ],
    "product_path": "^/itm/\\d+"
  }
];
