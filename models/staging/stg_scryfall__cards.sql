-- stg_scryfall__cards.sql

with

source as (

    select * from {{ source('scryfall', 'raw_scryfall_cards') }}

)

, renamed as (

    select

        ---------- ids
        cast(id as string) as id
        , cast(oracle_id as string) as oracle_id
        , cast(json_value(payload, '$.card_back_id') as string) as card_back_id
        , cast(json_value(payload, '$.illustration_id') as string) as illustration_id
        , cast(json_value(payload, '$.set_id') as string) as set_id
        , cast(json_value(payload, '$.tcgplayer_id') as string) as tcgplayer_id
        
        ---------- strings
        , cast(json_value(payload, '$.name') as string) as card_name
        , cast(json_value(payload, '$.artist') as string) as artist_name
        , cast(json_value(payload, '$.border_color') as string) as border_color
        , cast(json_value(payload, '$.image_status') as string) as image_status
        , cast(json_value(payload, '$.lang') as string) as card_language
        , cast(json_value(payload, '$.layout') as string) as layout
        , cast(json_value(payload, '$.mana_cost') as string) as mana_cost
        , cast(json_value(payload, '$.object') as string) as object_type
        , cast(json_value(payload, '$.oracle_text') as string) as oracle_text
        , cast(json_value(payload, '$.collector_number') as string) as collector_number
        , cast(json_value(payload, '$.prints_search_uri') as string) as prints_search_uri
        , safe_cast(json_value(payload, '$.purchase_uris.cardhoarder') as string) as purchase_uri_cardhoarder
        , safe_cast(json_value(payload, '$.purchase_uris.cardmarket') as string) as purchase_uri_cardmarket
        , safe_cast(json_value(payload, '$.purchase_uris.tcgplayer') as string) as purchase_uri_tcgplayer
        , safe_cast(json_value(payload, '$.related_uris.edhrec') as string) as related_uris_edhrec
        , safe_cast(json_value(payload, '$.related_uris.tcgplayer_infinite_articles') as string) as related_uris_tcgplayer_infinite_articles
        , safe_cast(json_value(payload, '$.related_uris.tcgplayer_infinite_decks') as string) as related_uris_tcgplayer_infinite_decks
        , cast(json_value(payload, '$.rulings_uri') as string) as rulings_uri
        , cast(json_value(payload, '$.scryfall_set_uri') as string) as scryfall_set_uri
        , cast(json_value(payload, '$.security_stamp') as string) as security_stamp
        , cast(json_value(payload, '$.set') as string) as set_code
        , cast(json_value(payload, '$.set_name') as string) as set_name
        , cast(json_value(payload, '$.set_uri') as string) as set_uri
        , cast(json_value(payload, '$.rarity') as string) as rarity
        , cast(json_value(payload, '$.type_line') as string) as type_line
        , cast(json_value(payload, '$.cmc') as string) as cmc
        , cast(json_value(payload, '$.loyalty') as string) as loyalty
        , cast(json_value(payload, '$.frame') as string) as frame
        , cast(json_value(payload, '$.power') as string) as power
        , cast(json_value(payload, '$.toughness') as string) as toughness
        , cast(json_value(payload, '$.uri') as string) as uri

        ---------- booleans
        , {{ is_legal("json_value(payload, '$.legalities.alchemy')") }} as is_legal_alchemy
        , {{ is_legal("json_value(payload, '$.legalities.brawl')") }} as is_legal_brawl
        , {{ is_legal("json_value(payload, '$.legalities.commander')") }} as is_legal_commander
        , {{ is_legal("json_value(payload, '$.legalities.competitivebrawl')") }} as is_legal_competitive_brawl
        , {{ is_legal("json_value(payload, '$.legalities.duel')") }} as is_legal_duel
        , {{ is_legal("json_value(payload, '$.legalities.future')") }} as is_legal_future
        , {{ is_legal("json_value(payload, '$.legalities.gladiator')") }} as is_legal_gladiator
        , {{ is_legal("json_value(payload, '$.legalities.historic')") }} as is_legal_historic
        , {{ is_legal("json_value(payload, '$.legalities.legacy')") }} as is_legal_legacy
        , {{ is_legal("json_value(payload, '$.legalities.modern')") }} as is_legal_modern
        , {{ is_legal("json_value(payload, '$.legalities.oathbreaker')") }} as is_legal_oathbreaker
        , {{ is_legal("json_value(payload, '$.legalities.oldschool')") }} as is_legal_oldschool
        , {{ is_legal("json_value(payload, '$.legalities.pauper')") }} as is_legal_pauper
        , {{ is_legal("json_value(payload, '$.legalities.paupercommander')") }} as is_legal_pauper_commander
        , {{ is_legal("json_value(payload, '$.legalities.penny')") }} as is_legal_penny
        , {{ is_legal("json_value(payload, '$.legalities.pioneer')") }} as is_legal_pioneer
        , {{ is_legal("json_value(payload, '$.legalities.predh')") }} as is_legal_predh
        , {{ is_legal("json_value(payload, '$.legalities.premodern')") }} as is_legal_premodern
        , {{ is_legal("json_value(payload, '$.legalities.standard')") }} as is_legal_standard
        , {{ is_legal("json_value(payload, '$.legalities.standardbrawl')") }} as is_legal_standard_brawl
        , {{ is_legal("json_value(payload, '$.legalities.timeless')") }} as is_legal_timeless
        , {{ is_legal("json_value(payload, '$.legalities.tlr')") }} as is_legal_tlr
        , {{ is_legal("json_value(payload, '$.legalities.vintage')") }} as is_legal_vintage
        
        , cast(json_value(payload, '$.reprint') as boolean) as is_reprint
        , cast(json_value(payload, '$.reserved') as boolean) as is_reserved
        , cast(json_value(payload, '$.variation') as boolean) as is_variation
        , cast(json_value(payload, '$.booster') as boolean) as is_booster
        , cast(json_value(payload, '$.digital') as boolean) as is_digital
        , {{ array_contains("json_value_array(payload, '$.finishes')", "'foil'") }} as is_foil
        , {{ array_contains("json_value_array(payload, '$.finishes')", "'nonfoil'") }} as is_non_foil
        , {{ array_contains("json_value_array(payload, '$.finishes')", "'etched'") }} as is_etched
        , cast(json_value(payload, '$.full_art') as boolean) as is_full_art
        , cast(json_value(payload, '$.game_changer') as boolean) as is_game_changer
        , cast(json_value(payload, '$.highres_image') as boolean) as has_highres_image
        , cast(json_value(payload, '$.oversized') as boolean) as is_oversized
        , cast(json_value(payload, '$.promo') as boolean) as is_promo
        , cast(json_value(payload, '$.story_spotlight') as boolean) as is_story_spotlight
        , cast(json_value(payload, '$.textless') as boolean) as is_textless

        ---------- numerics
        , cast(json_value(payload, '$.edhrec_rank') as integer) as edhrec_rank

        , safe_cast(json_value(payload, '$.prices.usd') as numeric) as price_usd
        , safe_cast(json_value(payload, '$.prices.usd_foil') as numeric) as price_usd_foil
        , safe_cast(json_value(payload, '$.prices.eur') as numeric) as price_eur
        , safe_cast(json_value(payload, '$.prices.tix') as numeric) as price_tix

        ---------- arrays
        , cast(json_value_array(payload, '$.keywords') as array<string>) as keywords
        , cast(json_value_array(payload, '$.multiverse_ids') as array<string>) as multiverse_ids

        ---------- timestamps
        , cast(json_value(payload, '$.released_at') as date) as released_at
        , cast(fetch_date as date) as fetch_date
        , cast(fetched_at as timestamp) as fetched_at
        , cast(json_value(payload, '$.image_updated_at') as timestamp) as image_updated_at

    from source

)

select * from renamed