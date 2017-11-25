# redis

## de-duplication
* image link
* image file

## latest downloaded缓存
hash: `latest_downloaded_ts:publisher`
hash: `latest_downloaded_ts:hashtag`


## earliest_downloaded_ts缓存
hash: `earliest_downloaded_ts:publisher`
hash: `earliest_downloaded_ts:hashtag`

## query_id的缓存
string:
    `queryid:publisher`
    `queryid:hashtag`
expiration:
    `settings.QUERYID_EXPIRES_IN`

## publisher/tag latest update time
sorted set: latest_update ts <tagname.hashtag|publisherid.publisher>
    
# updating
string update:<tagname.hashtag|publisherid.publisher>

# query_id
publisher和tag的query_id不同



GraphSidecar
tag相关页面中没有__typename字段