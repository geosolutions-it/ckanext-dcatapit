var dcatapit = window.dcatapit || {};

if (!String.prototype.startsWith) {
	String.prototype.startsWith = function(search, pos) {
    		return this.substr(!pos || pos < 0 ? 0 : +pos, search.length) === search;
    };
}


dcatapit.templated_input = {
        initialize: function(){
            $.proxyAll(this, /_on/);
            try {
                var val = $.parseJSON($(this.el).val() || '[]');
            } catch (SyntaxError){
                var val = [];
            }

            this.lang = this.options.lang;
            this.tmpl = $(this.options.template);
            this.container = $(this.options.container);
            this.val = val;


            this.sub_initialize();

            this.populate_items(this.val, this.tmpl, this.container);
            this.add_handlers($(this.el).parent());

        },

        /** per-subclass overrides
        */
        sub_initialize: function(){

        },
        sub_add_values: function(){

        },

        sub_set_error: function(){

        },

        /** install onclick handlers for main templates
        */
        add_handlers: function(ctx){
            var that = this;

            /* each container will have a configuration
               data-add-with - element selector that allows to add new elements from template
               data-add-template - element selector with template to add. it's good to have
                 this element with template class.
            */
            $('.add_new_container', ctx).each(function(idx, elm){
                var add_with_list = $($(elm).data("add-with"));


                add_with_list.each(function(ydx, add_with_elm){
                    var add_with = $(add_with_elm);
                    
                    // , $(elm).parent());
                    var tmpl = $($(elm).data('add-template'), $(elm).parent());

                    // marker to check if we didn't add handlers already
                    if (add_with.data('has-container-cb')){
                        return;
                    }

                    /* callback for onclick - add new template
                         and add callbacks for inputs to update main input after change
                    */
                    var h = function(evt){
                        var t = that.add_row(tmpl, elm, []);
                    }
                    add_with.data('has-container-cb', true);

                    add_with.click(h);
                });
            });
            var remove_h = function(evt){
                var elm = $(evt.delegateTarget);
                if (elm.data('remove-parent') !== undefined){
                    var out = elm.parents(elm.data('remove-parent'));
                } else {
                    var out = elm.parent();
                }
                out.remove();

            }
            $('.remove', ctx).click(remove_h);
        },

        add_row: function(template, container, values){
            var t = template.clone().removeClass('template');

            $(container).append(t[0]);
            this.add_values(t, values);
            this.add_handlers(t);
            return t;
        },

        add_values: function(ui, values){
            this.sub_add_values(ui, values);

            ui.data(this.options.data_name, values);
        },

        populate_items: function(values, template, tmpl_container){
            //clear container
            tmpl_container.html('');

            for (var i=0; i< values.length; i++){
                var value = values[i];
                var elm = this.add_row(template, tmpl_container, value);
                this.set_error(elm);

            }
        },

        set_error: function(elm){
            this.sub_set_error(elm);
        },
        extract_from_element: function(elms){
            var out = {};
            var existing = $(elms).data(this.options.data_name) || {};
            $.extend(out, existing);
            var lang = this.lang;
            var inputs = $('input, select', elms);
            var that = this;

            inputs.each(function(idx, elm){
                that.extract_from_each_element(idx, elm, out, lang);
            });
            return out;
        },
        extract_values: function(){
            var out = [];
            var containers = $(this.options.template, this.root);
            var that = this;
            containers.each(function(idx, elm){
                if ($(elm).hasClass('template')){
                    return;
                }
                var elval = that.extract_from_element(elm);
                out.push(elval);
                });

            // do any postprocessing if needed of extracted values
            out = this.post_extract(out);

            this.el.attr('value', JSON.stringify(out));
            return out;
        },
        post_extract: function(values){
            if (this._post_extract !== undefined){
                return this._post_extract(values);
            } else {
                return values;
            }
        }
     }

/** 
 Handles conforms to data edition.
*/
ckan.module('dcatapit-conforms-to', function($){
    var conforms_to = {

        sub_initialize: function(){
            this.add_form_handlers($(this.el.parent()));

            this.localized = ['title', 'description'];
        },
        /** 
            add submit event handler to disable input elements for elm
        */
        add_form_handlers: function(elm){
            var that = this;
            elm.parents('form').submit(
                function(){
                        var inputs = $('.conforms_to input', elm);
                        inputs.attr('disabled', true);
                        $('input[name=conforms_to]', elm).attr('disabled', false);
                        that.extract_values();
                   }
                 )
        },
        sub_add_values: function(ui, values){

            for (var k in values){
                var val = values[k];
                var input_name = this.options.input_prefix + k;

                if (k == 'referenceDocumentation'){
                    
                    var refdoc_ui = $('.reference_documentation.template', ui);
                    var refdocs_container = $('.reference_container', ui);

                    for (var i = 0; i< val.length; i++){
                        var refdoc_val = val[i];
                        var to_add = refdoc_ui.clone().removeClass('template');
                        refdocs_container.append(to_add);
                        $('input', to_add).attr('value', refdoc_val);

                    }

                } else {

                    if ($.inArray(k, this.localized)> -1){
                        var local_val = val[this.lang];
                    } else {
                        var local_val = val;
                    }

                    ui.find('input[name=' + input_name + ']').attr('value', local_val);
                    ui.attr('lang', this.lang);
                }
            }
        },

        extract_from_each_element: function(idx, elm, out, lang){
                var elm = $(elm);
                var _elm_name = elm.attr('name');
                var elm_name = _elm_name.slice(this.options.input_prefix.length);

                if (elm_name != 'referenceDocumentation'){
                    if ($.inArray(elm_name, this.localized)> -1){
                        if (!$.isPlainObject(out[elm_name])){
                        out[elm_name] = {};
                        }
                        var elval = elm.val();
                        if (elval !== ""){
                            out[elm_name][lang] = elval;
                        }
                    }
                    else {
                        var elval = elm.val();
                        if (typeof elval == 'string' && elval.trim() != ''){
                            out[elm_name] = elval;
                        }
                    }
                } else {
                    if (!$.isArray(out[elm_name])){
                        out[elm_name] = [];
                    }
                    var elval = elm.val();
                    if (elval !== ""){
                        // there can be older entries for this
                        if ($.inArray(elval, out[elm_name]) < 0){
                            out[elm_name].push(elval);
                        }
                    }
                }
        }
    };
    return $.extend({}, dcatapit.templated_input, conforms_to);
 });


ckan.module('dcatapit-alternate-identifier', function($){
    var alternate_identifier= {

        sub_initialize: function(){
            this.add_form_handlers($(this.el.parent()));
            this.localized = ['agent_name'];
        },
        /** 
            add submit event handler to disable input elements for elm
        */
        add_form_handlers: function(elm){
            var that = this;
            elm.parents('form').submit(
                function(){
                        var inputs = $('.alternate_identifier input', elm);
                        inputs.attr('disabled', true);
                        $('input[name=alternate_identifier]', elm).attr('disabled', false);
                        that.extract_values();
                   }
                 )
        },

        extract_from_each_element: function(idx, elm, out, lang){
                var elm = $(elm);
                var _elm_name = elm.attr('name');
                var elm_name = _elm_name.slice(this.options.input_prefix.length);
                var agent = out['agent'] || {};

                if (elm_name.startsWith('agent_')){
                    if ($.inArray(elm_name, this.localized)> -1){
                        if (!$.isPlainObject(agent[elm_name])){
                            agent[elm_name] = {};
                        }
                        var elval = elm.val();
                        if (elval !== ""){
                            agent[elm_name][lang] = elval;
                        }}
                   else {
                        agent[elm_name] = elm.val();

                        }
                } else {

                   out[elm_name] = elm.val();

                }
                out['agent'] = agent;
        },

        sub_add_values: function(ui, values){

            for (var k in values){
                var val = values[k];
                if (k == 'agent'){
                    for (var a in val){
                        var adata = val[a];

                        if ($.inArray(a, this.localized)> -1){
                            var local_val = adata[this.lang];
                        } else {
                            var local_val = adata;
                        }

                        var input_name = this.options.input_prefix + a;
                        ui.find('input[name=' + input_name + ']').attr('value', local_val);
                        ui.attr('lang', this.lang);
                    }
                } else {
                        var local_val = val;
                        var input_name = this.options.input_prefix + k;
                        ui.find('input[name=' + input_name + ']').attr('value', local_val);
                        ui.attr('lang', this.lang);
                }
            }

        },

    };
    return $.extend({}, dcatapit.templated_input, alternate_identifier);
 });


ckan.module('dcatapit-creator', function($){
    var creator = {

        sub_initialize: function(){
            this.add_form_handlers($(this.el.parent()));
            this.localized = ['creator_name'];
        },
        /** 
            add submit event handler to disable input elements for elm
        */
        add_form_handlers: function(elm){
            var that = this;
            elm.parents('form').submit(
                function(){
                        var inputs = $('input', elm);
                        inputs.attr('disabled', true);
                        $('input[name=creator]', elm).attr('disabled', false);
                        that.extract_values();
                   }
                 )
        },

        extract_from_each_element: function(idx, elm, out, lang){
                var elm = $(elm);
                var _elm_name = elm.attr('name');
                var elm_name = _elm_name.slice(this.options.input_prefix.length);
                var elval = elm.val();
                if ($.inArray(elm_name, this.localized) >-1){
                    if (!$.isPlainObject(out[elm_name])){
                        out[elm_name] = {};
                    }
                    if (elval !== ""){
                        out[elm_name][lang] = elval;
                    }
                } else {
                    out[elm_name] = elval;
                }
        },

        sub_add_values: function(ui, values){

            for (var k in values){
                var val = values[k];
                var local_val = val;
                if ($.inArray(k, this.localized)>-1){
                    local_val = val[this.lang];
                }
                var input_name = k //this.options.input_prefix + k;
                ui.find('input[name=' + input_name + ']').attr('value', local_val);
                ui.attr('lang', this.lang);
            }
        },

    };
    return $.extend({}, dcatapit.templated_input, creator);
 });

ckan.module('dcatapit-temporal-coverage', function($){
    var temporal_coverage = {

        sub_initialize: function(){
            this.add_form_handlers($(this.el.parent()));
            this.localized = [];
        },
        /** 
            add submit event handler to disable input elements for elm
        */
        add_form_handlers: function(elm){
            var that = this;
            elm.parents('form').submit(
                function(){
                        var inputs = $('input', elm);
                        inputs.attr('disabled', true);
                        $('input[name=temporal_coverage]', elm).attr('disabled', false);
                        that.extract_values();
                   }
                 )
        },

        extract_from_each_element: function(idx, elm, out, lang){
                var elm = $(elm);
                var _elm_name = elm.attr('name');
                var elm_name = _elm_name.slice(this.options.input_prefix.length);
                var val = elm.val();
                if (typeof val == 'string' && val.trim() != ''){
                    out[elm_name] = val;
                }
        },

        sub_add_values: function(ui, values){

            for (var k in values){
                var val = values[k];
                var local_val = val;
                var input_name = k //this.options.input_prefix + k;
                ui.find('input[name=' + input_name + ']').attr('value', local_val);
                ui.attr('lang', this.lang);
            }
        },
        sub_set_error: function(elm){
            if (typeof this.options.error == 'string' && this.options.error.length> 1){

                $('.control-group', elm).addClass('error');
            }
        },
        _post_extract: function(values){
            var out = [];

            var _qualifies = function(value){
                if (typeof value == 'string' && value.trim() !== ''){
                    return value;
                }
                return null;
            }
            // remove empty rows, or rows with no temporal_start
            $.each(values, function(rowidx, row) {
                var tstart = _qualifies(row['temporal_start']);
                var tend = _qualifies(row['temporal_end']);
                if (! (tstart == null && tend == null)){
                    out.push(row);
                }
            });
            return out;
        }

    };
    return $.extend({}, dcatapit.templated_input, temporal_coverage);
 });


ckan.module('geonames', function($){
    var geonames = {
        initialize: function(){
            $.proxyAll(this, /_on/);
            var username = this.options.geonamesUsername;
            try { 
                var limit_to = this.options.geonamesLimitTo.split(' ');
            }
            catch (err){
                var limit_to = [];
            }
            var el = $(this.el);
            jeoquery.defaultData.userName = username;
            jeoquery.defaultData.country = limit_to;
            if (this.options.geonamesLanguage !== undefined && this.options.geonamesLanguage !== false){
                jeoquery.defaultLanguage = this.options.geonamesLanguage;
            }
            var that = this;
            // where to store geonames url (hidden input)
            
            this.store = $(this.options.geonamesStore);
            // where to display geonames url (span)
            // this.display = $(this.options.geonamesDisplay);
            
            this.enable();
            var init_val = this.store.val();
            if (init_val){
                this.store.html('loading..');
                this.load_for(this.store.val());
            }
            this.geonames = el.jeoCityAutoComplete({'country': limit_to,
                                                    'lang': this.options.geonamesLanguage,
                                                    'callback': function(data){return that.on_names(data)}});
        },

        enable: function(){
            var that = this;
            // this.store.attr('type', 'hidden');
            //this.display.removeClass('hidden');
            $(this.el).attr('readonly', false);
            this.store.change(function(evt){
                                that.on_url_change(evt)});

        },

        load_for: function(value){
            var that = this;
            var url = this.normalize_url(value);
            if (url == null){
                return;
            }
            var geonameId = url.split('/')[3];
            this.el.attr('readonly', true);
            var gn = jeoquery.getGeoNames('get',
                                          {'geonameId': geonameId},
                                          function(details){ 
                                                    that.el.attr('readonly', false);
                                                    return that.on_names(details, true)
                                                    });
        },
        
        normalize_url: function(val){
            if (val == undefined || $.trim(val) == ""){
                return null;
            }
            var id = null;
            if (val.startsWith('http://geonames.org/') || val.startsWith('https://geonames.org/')){
                id = val.split('/')[3];
            } else if (val.startsWith('geonames.org/')){
                id = val.split('/')[1];
            } else {
                id = val;
            }
            if ($.isNumeric(id)){
                return 'http://geonames.org/' + parseInt(id);
            }
            return null;
        },

        on_url_change: function(evt){
            var val = $(evt.delegateTarget).val() || "";
            var url = this.normalize_url(val);
            if (url == null){
                return;
            }
            this.load_for(url, true);
        },
        on_names: function(details, is_init){
            if (details.geonameId == undefined){
                return;
            }
            var url = 'https://geonames.org/' + details.geonameId;
            this.store.attr('value', url);
            //this.display.html(url);
            if (is_init == true){
                $(this.el).attr('value', details.name + ',' + details.adminName1 + ', '+ details.countryName);
            }
        }

    };
    return $.extend({}, geonames);
 });


ckan.module('dcatapit-help', function($){
    var help = {
        initialize: function(){
            $.proxyAll(this, /_on/);
            $(this.el.find('i')).tooltip();
        }
    }

    return $.extend({}, help);

 });


ckan.module('dcatapit-theme', function($){
    var theme = {
        sub_initialize: function(){
            this.add_form_handlers($(this.el.parent()));
            this.localized = [];
        },
        /** 
            add submit event handler to disable input elements for elm
        */
        add_form_handlers: function(elm){
            var that = this;
            elm.parents('form').submit(
                function(){
                        var inputs = $('select', elm);
                        inputs.attr('disabled', true);
                        $('input[name=theme]', elm).attr('disabled', false);
                        that.extract_values();
                   }
                 )
        },

        extract_from_each_element: function(idx, elm, out, lang){
                var elm = $(elm);
                var _elm_name = elm.attr('name');
                // selec2 autogen
                if (_elm_name == undefined){
                    return;
                }

                var elm_name = _elm_name.slice(this.options.input_prefix.length);
                var val = elm.val();

                if (elm_name == 'theme'){
                    if (typeof val == 'string' && val.trim() != ''){
                        out['theme'] = val;
                    }
                } else {
                    // 
                    sublist = elm.select2('data');
                    out['subthemes'] = [];
                    $.each(sublist, function(idx, sel){
                            out['subthemes'].push(sel['id']);
                    });
                }
        },

        sub_add_values: function(ui, values){
            var that = this;

            var selected_theme = values['theme'];
            $('select.theme_select', ui).val(selected_theme);
            that.set_subthemes(ui, values);

            var ac = ckan.module.registry['autocomplete'];
            var sel = ui.find('select')
            var sel_theme = ui.find('select.theme_select');
            sel.attr('data-module', 'autocomplete');

            sel.each(function(idx, elm){
                ckan.module.createInstance(ac, elm);
            });

            sel_theme.change(
                    function(evt){
                        that.clear_subthemes(ui);
                        that.set_subthemes(ui);
                        }
                    );
        },
        clear_subthemes: function(elm){
            var sel = $('select.subtheme_select', elm);
            sel.select2('data', []);
            sel.html('');
        },
        set_subthemes: function(elm, selected){
            if (selected !== undefined){
                var selected_subthemes = selected['subthemes'];
            } else {
                var selected_subthemes = [];
            }
            var sel = $('select.subtheme_select', elm);
            var theme_sel = $('select.theme_select', elm);
            var target_theme = theme_sel.val();

            var opts = dcatapit.subthemes[target_theme];
            if (opts!= undefined){
                sel.html('');
                for (var i=0; i< opts.length; i++){
                    var opt = opts[i];
                    var sel_op = $('<option value="'+opt['value'] + '">' + opt['name'] + '</option>')

                    sel.append(sel_op);
                    if ($.inArray(opt['value'], selected_subthemes)>-1){
                        sel_op.prop('selected', true);
                        }
                    }
            }
        }
    }
    return $.extend({}, dcatapit.templated_input, theme);
 });

ckan.module('dcatapit-edit-form', function($){
    var edit_form = {
        initialize: function(){
            if (this.has_errors()){
                console.log('form with errors');
            }
            this.el = $(this.el);
            $.proxyAll(this, /_on/);
            this.settings = this.load_settings(this.options.settingsContainer);
            this.container = $(this.options.formContainer);
            this.init_tabs(this.settings, this.container);
        },

        get_errors: function(){
            return $('.error-explanation.alert');
        },
        has_errors: function(){
            var err = this.get_errors();
            return err.length > 0;
        },

        load_settings: function(container){
            var serialized_settings = $(container).html();
            try {
                var val = $.parseJSON(serialized_settings);
            } catch (err){
                console.log('cannot parse', serialized_settings, err);
                var val = {'tabs': []};
            }
            return val;
        },

        init_tabs: function(settings, container){
            var that = this;

            // where tabs are added
            var tabs_list = $('<ul id="form-tabs" class="unstyled nav nav-simple nav-facets"></ul>');
            // where form fields are moved
            var tabs_container = $('<div class="forms-container"></div>');

            container.prepend(tabs_container);
            container.prepend(tabs_list);

            $.each(settings['tabs'], function(idx, elm){
                var this_tab = that.add_tab(tabs_list,
                                            tabs_container,
                                            elm['id'],
                                            elm['name'],
                                            elm['fields']);
                if (elm['use_extra']||false){
                    that.collect_extras(this_tab, elm);
                }
            });
            // initiate tabs
            container.tabs({'activate': function(evt, ui){
                                                        $(ui.newTab).addClass('hovered');
                                                        $(ui.oldTab).removeClass('hovered');
                                                        return true;
                                                        
                                                        }});

            $(tabs_list.find('li')[0]).addClass('hovered').find('a').click();
            // move tabs controls to secondary content
            $('#tabs-container').append(tabs_list);
            this.build_nav(tabs_list.find('li'), tabs_container.find('.ui-tabs-panel'));
            this.handle_errors(tabs_list.find('li'), tabs_container.find('.ui-tabs-panel'), container);
            container.prepend($('ol.stages'));
        },

        handle_errors: function(tabs, panels, main_c){
            var err = this.get_errors();
            if (err.length > 0){
                main_c.prepend(err);
            }
            $.each(panels, function(idx, panel){
                var got_errors = $(panel).find('.error-block').length > 0;
                if (got_errors){
                    $(tabs[idx]).addClass('with-error');
                }

            });;


        
        },

        build_nav: function(tabs, panels){
            var that = this;
            $.each(tabs, function(idx, elm){
                var next = null;
                var prev = null;
                var current = $(elm);
                if (idx == 0){
                    if (tabs.length > 1){
                        next = $(tabs[idx+1]);
                    }
                } else if (idx < tabs.length) {
                    next = $(tabs[idx+1]);
                    prev = $(tabs[idx-1]);

                } else {
                    prev = $(tabs[idx-1]);
                }
                var panel = $(panels[idx]);
                that.add_nav(prev, next, panel);
            });

        },

        add_nav: function(prev_tab, next_tab, panel){
            var nav = $('<div class="form-nav"></div>');
            if (prev_tab !== null){
                var title = prev_tab.find('a span').html();
                var prev = $('<span class="prev-item form-nav-item btn btn-small"><a title="prev: '+ title +'" href="#">'+ title +'</a></span>');
                nav.append(prev);
                prev.find('a').click(function(){ prev_tab.find('a').click()});
            }
            if (next_tab !== null){
                var title = next_tab.find('a span').html();
                if (title !== undefined){
                    var next = $('<span class="next-item form-nav-item btn btn-small"><a title="next: '+ title +'" href="#">'+ title +'</a></span>');
                    nav.append(next);
                    next.find('a').click(function(){ next_tab.find('a').click()});
                }
            }
            panel.append(nav);
        },

        collect_extras: function(to_tab, config){
            var tabs = to_tab['tab'];
            var form = to_tab['form'];
            var parent_name  = config['parent'] || '.control-group';

            var extras = $('[data-module="custom-fields"]');
            form.append(extras);

            /*
            var extras = [];
            var extras_in = $('[name^="extras__"]');

            $.each(extras_in, function(idx, elm){
                var parent_elm = $(elm).parents(parent_name);
                if (parent_elm.length>0 && $.inArray(parent_elm[0], extras) < 0){
                    form.append($(parent_elm[0]));
                }
            });
            */
        },

        add_tab: function(tabs_container, container, tab_id, name, fields){
            var tab = $('<li class="nav-item"><a href="#' + tab_id + '-tab-container"><span>'+ name +'</span></a></li>');
            var form_p = $('<div id="'+ tab_id+'-tab-container"></div>');
            var that = this;
            container.append(form_p);
            tabs_container.append(tab);

            $.each(fields, function(idx, elm){
                if (elm['selector'] !== undefined){
                    var field = $(elm['selector']);
                } else {
                    var field = $('[name="' + elm['name'] +'"]');
                }
                // customized parent lookup
                var parent_name  = elm['parent'] || '.control-group';
                var field_container = field.parents(parent_name);
                if  (field_container.length > 0){
                    form_p.append(field_container);
                }
            });
            return {'tab': tab, 'form': form_p}
        }
    }

    return $.extend({}, edit_form);
 });
