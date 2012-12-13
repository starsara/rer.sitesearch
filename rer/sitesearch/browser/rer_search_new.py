# -*- coding: utf-8 -*-
from DateTime import DateTime
from plone.app.contentlisting.interfaces import IContentListing
from plone.app.search.browser import Search
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.browser.navtree import getNavigationRoot
from Products.CMFPlone.PloneBatch import Batch
from Products.ZCTextIndex.ParseTree import ParseError
from rer.sitesearch import sitesearchMessageFactory as _
from zope.i18n import translate
from ZTUtils import make_query
from DateTime import DateTime
from ZPublisher.HTTPRequest import record
from rer.sitesearch.interfaces import IRERSiteSearchSettings
from zope.component import queryUtility
from plone.registry.interfaces import IRegistry


MULTISPACE = u'\u3000'.encode('utf-8')
EVER = DateTime('1970-01-03')


def quote_chars(s):
    # We need to quote parentheses when searching text indices
    if '(' in s:
        s = s.replace('(', '"("')
    if ')' in s:
        s = s.replace(')', '")"')
    if MULTISPACE in s:
        s = s.replace(MULTISPACE, ' ')
    return s


class RERSearch(Search):
    """
    """

    def __init__(self, context, request):
        """
        """
        super(RERSearch, self).__init__(context, request)
        self.catalog = getToolByName(self.context, 'portal_catalog')
        self.search_settings = self.getSearchSettings()
        self.tabs_order = self.getRegistryInfos('tabs_order')
        self.indexes_order = self.getRegistryInfos('indexes_order')

    @property
    def tabs_mapping(self):
        tabs_map = self.getRegistryInfos('tabs_mapping')
        tabs_dict = {'all': {'title': 'All'}}
        for tab in tabs_map:
            tab_title = tab.tab_title
            tab_id = tab_title.lower().replace(' ', '-')
            tabs_dict[tab_id] = {'title': tab_title, 'portal_types': tab.portal_types}
        return tabs_dict

    @property
    def types_mapping(self):
        tabs_map = self.getRegistryInfos('tabs_mapping')
        types_dict = {}
        for tab in tabs_map:
            tab_id = tab.tab_title.lower().replace(' ', '-')
            tab_types = tab.portal_types
            for portal_type in tab_types:
                types_dict[portal_type] = tab_id
        return types_dict

    @property
    def available_indexes(self):
        indexes_map = self.getRegistryInfos('available_indexes')
        indexes_dict = {}
        for index in indexes_map:
            indexes_dict[index.index] = index.index_title
        return indexes_dict

    @property
    def hidden_indexes(self):
        indexes_map = self.getRegistryInfos('hidden_indexes')
        indexes_dict = {}
        for index in indexes_map:
            indexes_dict[index.index] = index.index_title
        return indexes_dict

    def getRegistryInfos(self, registry_item):
        """
        Return a value stored in plone.app.registry.
        @param: registry_item
        """
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IRERSiteSearchSettings, check=False)
        if not settings:
            return None
        return getattr(settings, registry_item, None)

    @property
    def valid_keys(self):
        """
        """
        valid_keys = ['sort_on', 'sort_order', 'sort_limit', 'fq', 'fl', 'facet', 'filter_tab']
        hidden_indexes = self.hidden_indexes
        for index in hidden_indexes.keys():
            if index not in valid_keys:
                    valid_keys.append(index)
        return tuple(valid_keys)

    def splitSearchOptions(self, value):
        """
        This method returns key and value. If there isn't a value, return the key as value
        @param: value is a string that contain a key and a value divided by "pipe" character
        """
        key_info = value.split('|')
        if len(key_info) == 2:
            return {'id': key_info[0], 'title': key_info[1]}
        else:
            return {'id': key_info[0], 'title': key_info[0]}

    def getSelectedTab(self, tabs):
        """
        """
        tab_in_request = self.request.form.get('filter_tab', '')
        if tab_in_request:
            return tab_in_request
        else:
            for tab in self.tabs_order:
                if tab in tabs:
                    return tab
        return "all"

    # def getSearchSettings(self):
    #     portal_properties = getToolByName(self.context, 'portal_properties')
    #     rer_properties = getattr(portal_properties, 'rer_properties', None)
    #     if not rer_properties:
    #         return []
    #     tabs_settings = rer_properties.getProperty('tabs_list', ())
    #     keywords = rer_properties.getProperty('indexes_in_search', ())
    #     whitelist = rer_properties.getProperty('type_whitelist', ())
    #     hiddenlist = rer_properties.getProperty('indexes_hiddenlist', ())
    #     indexes_order = []
    #     indexes_map = {}
    #     tabs_dict = {}
    #     if not keywords:
    #         keywords = rer_properties.getProperty('keywordview_properties', ())
    #     if keywords:
    #         for index in keywords:
    #             index_values = self.splitSearchOptions(index)
    #             index_id = index_values.get('id', '')
    #             index_title = index_values.get('title', '')
    #             if index_id and index_title:
    #                 indexes_order.append(index_id)
    #                 indexes_map[index_id] = {'title': index_title}
    #     else:
    #         indexes_order.append('Subject')
    #     if tabs_settings:
    #         tabs_dict = self.setTabsInfos(tabs_settings)
    #     return {'indexes': indexes_map,
    #             'indexes_order': indexes_order,
    #             'whitelist': whitelist,
    #             'hiddenlist': hiddenlist,
    #             'tabs_dict': tabs_dict}

    # def setTabsInfos(self, tab_infos):
    #     """
    #     """
    #     tabs_dict = {'tabs_order': [], 'tabs_mapping': {}}
    #     for tab in tab_infos:
    #         tab_values = self.splitSearchOptions(tab)
    #         tab_id = tab_values.get('id', '')
    #         tab_title = tab_values.get('title', '')
    #         if tab_id and tab_title:
    #             tab_name = tab_title.lower().replace(' ', '-')
    #             tabs_dict['tabs_mapping'][tab_id] = tab_name
    #             if not tabs_dict.get(tab_name, {}):
    #                 tabs_dict[tab_name] = {'portal_types': [tab_id],
    #                                        'title': tab_title}
    #             else:
    #                 tabs_dict[tab_name].get('portal_types', []).append(tab_id)
    #             if tab_name not in tabs_dict['tabs_order']:
    #                 tabs_dict['tabs_order'].append(tab_name)
    #     if "all" not in tabs_dict['tabs_order']:
    #         tabs_dict["all"] = {'title': "All"}
    #         tabs_dict['tabs_order'].append('all')
    #     return tabs_dict

    def results(self, query=None, batch=True, b_size=20, b_start=0, tab=''):
        """ Get properly wrapped search results from the catalog.
        Everything in Plone that performs searches should go through this view.
        'query' should be a dictionary of catalog parameters.
        """
        if query is None:
            query = {}
        # if batch:
        #     query['b_start'] = b_start = int(b_start)
        #     query['b_size'] = b_size
        query = self.filter_query(query)
        res_dict = {}
        filtered_results = []
        if query is None:
            results = []
        else:
            try:
                results = self.catalog(**query)
            except ParseError:
                return []
        if tab != "all":
            res_dict = {'tot_results_len': results.actual_result_count}
            if tab:
                filtered_results = self.doFilteredSearch(tab, query)
            else:
                for tab_id in self.tabs_order:
                    filtered_results = self.doFilteredSearch(tab_id, query)
                    if filtered_results:
                        break
        filtered_infos, available_tabs = self.getFilterInfos(results, filtered_results)
        if tab != "all" or filtered_results:
            results = IContentListing(filtered_results)
        else:
            results = IContentListing(results)
        self.context.plone_log("Risultati: %s" % len(results))

        if batch:
            results = Batch(results, b_size, b_start)
        res_dict['results'] = results
        if filtered_infos:
            res_dict['indexes_dict'] = filtered_infos
        res_dict['tabs'] = available_tabs
        return res_dict

    def doFilteredSearch(self, tab, query):
        """
        """
        tab_infos = self.tabs_mapping.get(tab, {})
        if tab_infos:
            types_filter = tab_infos.get('portal_types', ())
            if types_filter:
                query['portal_type'] = types_filter
                return self.catalog(**query)

    def getFilterInfos(self, results, filtered_results=[]):
        """
        """
        indexes_order = self.indexes_order
        indexes_mapping = self.available_indexes
        #filter_dict = {'indexes_order': indexes_order}
        filter_dict = {}
        #tabs_dict = self.search_settings.get('tabs_dict', {})
        available_tabs = ['all']
        types_mapping = self.types_mapping
        for item in results:
            tab_id = types_mapping.get(item.portal_type, '')
            if tab_id and tab_id not in available_tabs:
                available_tabs.append(tab_id)
            if not filtered_results:
                for index_id in indexes_order:
                    index_values = self.setIndexesListForItem(item, index_id)
                    if index_values:
                        if index_id not in filter_dict:
                            filter_dict[index_id] = {'title': indexes_mapping.get(index_id, index_id),
                                                     'values': set()}
                        filter_dict[index_id]['values'] = filter_dict[index_id]['values'].union(index_values)
        if filtered_results:
            for item in filtered_results:
                for index_id in indexes_order:
                    index_values = self.setIndexesListForItem(item, index_id)
                    if index_values:
                        if index_id not in filter_dict:
                            filter_dict[index_id] = {'title': indexes_mapping.get(index_id, index_id),
                                                     'values': set()}
                        filter_dict[index_id]['values'] = filter_dict[index_id]['values'].union(index_values)
        return filter_dict, available_tabs

    def setIndexesListForItem(self, brain, index_id):
        """
        Update results dict with indexes values of the given brain
        """
        index_value = getattr(brain, index_id, '')
        if not index_value:
            return set()
        if callable(index_value):
            return set(index_value())
        elif isinstance(index_value, tuple) or isinstance(index_value, list):
            return set(index_value)
        else:
            return set([index_value])

    def filter_query(self, query):
        request = self.request
        text = query.get('SearchableText', None)
        if text is None:
            text = request.form.get('SearchableText', '')
        # if not text:
        #     # Without text, the only meaningful case is Subject
        #     subjects = request.form.get('Subject')
        #     if not subjects:
        #         return
        catalog = getToolByName(self.context, 'portal_catalog')
        valid_keys = self.valid_keys + tuple(catalog.indexes())
        for k, v in request.form.items():
            query[k] = self.setFilteredIndex(k, v, valid_keys)
        if text:
            query['SearchableText'] = quote_chars(text)

        # don't filter on created at all if we want all results
        created = query.get('created')
        if created:
            if created.get('query'):
                if created['query'][0] <= EVER:
                    del query['created']

        # respect `types_not_searched` setting
        # types = query.get('portal_type', [])
        # if 'query' in types:
        #     types = types['query']
        # query['portal_type'] = self.filter_types(types)
        # respect effective/expiration date
        query['show_inactive'] = False
        # respect navigation root
        if 'path' not in query:
            query['path'] = getNavigationRoot(self.context)

        return query

    def setFilteredIndex(self, key, value, valid_keys):
        """
        """
        if value and ((key in valid_keys) or key.startswith('facet.')):
            if isinstance(value, list) or isinstance(value, tuple):
                return {"query": value,
                        "operator": "and"}
            else:
                return value
        else:
            return value

    def setQueryUrl(self, query={}, remove_indexes=[]):
        q = {}
        q.update(self.request.form)
        if query:
            q.update(query)
        if remove_indexes:
            for index in remove_indexes:
                if index in q:
                    del q[index]
        base_url = self.request.URL
        # After the AJAX call the request is changed and thus the URL part of
        # it as well. In this case we need to tweak the URL to point to have
        # correct URLs
        if '@@updated_search' in base_url:
            base_url = base_url.replace('@@updated_search', '@@search')
        return base_url + '?' + make_query(q)

    def getResultsLen(self, results_dict):
        """
        Return the updated and translated len results.
        @param: results_dict
        """
        results = results_dict.get('results', None)
        if not results:
            return 0
        results_len = results.sequence_length
        total_len = results_dict.get('tot_results_len', results_len)
        if not results_len and not total_len:
            return 0
        return translate(_("${results_len} on ${total_len}",
                          mapping={'results_len': results_len, 'total_len': total_len}),
                        context=self.request)
        # return "%s on %s" % (results_len, total_len)

    def indexesChecked(self, index_name):
        """
        Return a list of selected values for a given index_id
        """
        values = self.request.form.get(index_name, None)
        if not values:
            return []
        if isinstance(values, list):
            return values
        elif getattr(values, 'query', None):
            return values.query
        else:
            return []

    ### HIDDEN INDEXES ###
    def getHiddenIndexes(self):
        """
        Return a list of hidden indexes to insert in the query
        """
        hiddenlist = self.hidden_indexes
        hidden_dict = {'index_titles': [],
                       'index_ids': [],
                     'index_to_add': []}
        if not hiddenlist:
            return hidden_dict
        for index_id in hiddenlist:
            index_value = self.context.REQUEST.form.get(index_id, '')
            if not index_value:
                continue
            register_index = False
            index_title = hiddenlist.get(index_id, index_id)
            if isinstance(index_value, record):
                register_index = self.setHiddenRecord(index_value, index_id, hidden_dict)
            elif isinstance(index_value, list):
                register_index = self.setHiddenList(index_value, index_id, hidden_dict)
            else:
                register_index = True
                hidden_dict['index_to_add'].append({'id': index_id,
                                       'value': index_value})
            if register_index:
                hidden_dict['index_titles'].append(index_title)
                hidden_dict['index_ids'].append(index_id)
        return hidden_dict

    def setHiddenList(self, index_value, index, hidden_dict):
        """
        set the hidden index if is a list
        """
        has_values = False
        for value in index_value:
            if value:
                has_values = True
                index_id = "%s:list" % (index)
                hidden_dict['index_to_add'].append({'id': index_id,
                                           'value': value})
        return has_values

    def setHiddenRecord(self, index_value, index, hidden_dict):
        """
        set the hidden index if is a record
        """
        has_values = False
        if index_value.get('query', '') in ['', ['', '']]:
            return has_values
        for query_part in index_value.keys():
            index_id = "%s.%s:record" % (index, query_part)
            query_value = index_value[query_part]
            if not query_value:
                continue
            has_values = True
            if isinstance(query_value, list):
                index_id += ":list"
                for value_item in query_value:
                    if isinstance(value_item, DateTime):
                        index_id += ":date"
                        list_value = value_item.ISO()
                        hidden_dict['index_to_add'].append({'id': index_id,
                                               'value': list_value})
                    else:
                        hidden_dict['index_to_add'].append({'id': index_id,
                                               'value': value_item})
            else:
                hidden_dict['index_to_add'].append({'id': index_id,
                                       'value': query_value})
        return has_values

    def getFolderName(self, path):
        """
        Return folder Title, if exist
        """
        folder = self.context.unrestrictedTraverse(path, None)
        if folder:
            return folder.Title()
        else:
            return path