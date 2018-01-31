var dcatapit = window.dcatapit || {};

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
                var add_with = $($(elm).data("add-with"), $(elm).parent());
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
            this.el.val(JSON.stringify(out));
            return out;
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
                        $('input', to_add).val(refdoc_val);

                    }

                } else {

                    if ($.inArray(k, this.localized)> -1){
                        var local_val = val[this.lang];
                    } else {
                        var local_val = val;
                    }

                    ui.find('input[name=' + input_name + ']').val(local_val);
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
                        out[elm_name] = elval;
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
                        ui.find('input[name=' + input_name + ']').val(local_val);
                        ui.attr('lang', this.lang);
                    }
                } else {
                        var local_val = val;
                        var input_name = this.options.input_prefix + k;
                        ui.find('input[name=' + input_name + ']').val(local_val);
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
                ui.find('input[name=' + input_name + ']').val(local_val);
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
                out[elm_name] = elm.val();
        },

        sub_add_values: function(ui, values){

            for (var k in values){
                var val = values[k];
                var local_val = val;
                var input_name = k //this.options.input_prefix + k;
                ui.find('input[name=' + input_name + ']').val(local_val);
                ui.attr('lang', this.lang);
            }
        },
        sub_set_error: function(elm){
            if (typeof this.options.error == 'string' && this.options.error.length> 1){

                $('.control-group', elm).addClass('error');
            }
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
                return 'http://geonames.org/' + Number.parseInt(id);
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
            this.store.val(url);
            //this.display.html(url);
            if (is_init == true){
                $(this.el).val(details.name + ',' + details.adminName1 + ', '+ details.countryName);
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

                if (elm_name == 'theme'){
                    out['theme'] = elm.val();
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
                    if ($.inArray(sel_op.val(), selected_subthemes)>-1){
                        sel_op.prop('selected', true);
                        }
                    }
            }
        }
    }
    return $.extend({}, dcatapit.templated_input, theme);
 });
