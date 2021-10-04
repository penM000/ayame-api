from .database import mongodb_query
import datetime
import pprint


class ayame_query_class():
    async def pageid_match(self, pageid, date=None, _filter={"_id": 0}):
        """
        idの完全一致
        """
        if date is not None:
            try:
                date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
                date = str(date)
            except ValueError:
                date = None

        query_id = mongodb_query.perfect_match("id", pageid)

        if date is None:
            query = query_id
            cursor = mongodb_query.collection_search.find_one(query, _filter)
        else:
            query_date = mongodb_query.perfect_match("date", date)
            query = mongodb_query.and_query(query_id, query_date)
            cursor = mongodb_query.collection_data.find_one(query, _filter)
        result = await cursor
        return result

    async def title_partial_match(self, title, limit=0, _filter={"_id": 0}):
        """
        fullnameもしくはmetatitleの部分一致
        """
        query_metatitle = mongodb_query.partial_match("metatitle", title)
        query_fullname = mongodb_query.partial_match("fullname", title)
        query = mongodb_query.or_query(query_fullname, query_metatitle)

        cursor = mongodb_query.collection_search.find(
            query, _filter).sort("rating", -1).limit(limit)
        # pprint.pprint(await cursor.explain())
        result = [doc async for doc in cursor]
        return result

    async def title_perfect_match(self, title, _filter={"_id": 0}):
        """
        fullnameもしくはmetatitleの完全一致
        """
        query_metatitle = mongodb_query.perfect_match("metatitle", title)
        query_fullname = mongodb_query.perfect_match("fullname", title)

        query = mongodb_query.or_query(query_fullname, query_metatitle)
        cursor = mongodb_query.collection_search.find_one(query, _filter)
        result = await cursor
        return result

    async def tag_partial_match(self, tags, limit=0, _filter={"_id": 0}):
        """
        tagの部分一致and検索
        """
        query = None
        for tag in tags:
            query_temp = mongodb_query.partial_match("tags", tag)
            if query is None:
                query = mongodb_query.and_query(query_temp)
            else:
                query = mongodb_query.and_query(query, query_temp)
        cursor = mongodb_query.collection_search.find(
            query, _filter).sort("rating", -1).limit(limit)
        # pprint.pprint(await cursor.explain())
        result = [doc async for doc in cursor]
        return result

    async def create_at_range_match(self, _from, _to, limit=0, _filter={"_id": 0}):
        try:
            gte = datetime.datetime.strptime(_from, '%Y-%m-%d')
            lte = datetime.datetime.strptime(_to, '%Y-%m-%d')
        except ValueError:
            return []
        query = mongodb_query.range_match("created_at", gte=gte, lte=lte)
        cursor = mongodb_query.collection_search.find(
            query, _filter).sort("rating", -1).limit(limit)
        # pprint.pprint(await cursor.explain())
        result = [doc async for doc in cursor]
        return result

    async def complex_search(self,
                             title,
                             tags,
                             author,
                             rate_min,
                             rate_max,
                             date_from,
                             date_to,
                             page,
                             show,
                             _filter={"_id": 0}):

        queries = []
        if title is not None:
            # title検索クエリ
            query_metatitle = mongodb_query.partial_match("metatitle", title)
            query_fullname = mongodb_query.partial_match("fullname", title)
            query = mongodb_query.or_query(query_fullname, query_metatitle)
            queries.append(query)
        if tags is not None:
            # タグ検索クエリ
            query = None
            for tag in tags:
                query_temp = mongodb_query.partial_match("tags", tag)
                if query is None:
                    query = mongodb_query.and_query(query_temp)
                else:
                    query = mongodb_query.and_query(query, query_temp)
            queries.append(query)
        if author is not None:
            query = mongodb_query.partial_match("created_by_unix", author)
            queries.append(query)
        if rate_min is not None:
            query = mongodb_query.range_match("rating", gte=rate_min)
            queries.append(query)
        if rate_max is not None:
            query = mongodb_query.range_match("rating", lte=rate_max)
            queries.append(query)
        if date_from is not None:
            query = mongodb_query.range_match("created_at", gte=date_from)
            queries.append(query)
        if date_to is not None:
            query = mongodb_query.range_match("created_at", lte=date_to)
            queries.append(query)

        query = mongodb_query.and_query(*queries)

        cursor = mongodb_query.collection_search.find(query, _filter).sort(
            "rating", -1).skip(show * (page - 1)).limit(show * page)
        # pprint.pprint(await cursor.explain())
        result = [doc async for doc in cursor]
        return result


ayame_query = ayame_query_class()
