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
            var tabs_list = $('<ul id="form-tabs" class="unstyled nav nav-simple"></ul>');
            // where form fields are moved
            var tabs_container = $('<div class="forms-container"></div>');

            container.prepend(tabs_list);
            container.prepend(tabs_container);

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
                                                        }});

            $(tabs_list.find('li a')[0]).click();
            // move tabs controls to secondary content
            $('#tabs-container').append(tabs_list);
            this.build_nav(tabs_list.find('li'), tabs_container.find('.ui-tabs-panel'));
            this.handle_errors(tabs_list.find('li'), tabs_container.find('.ui-tabs-panel'), container);
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
                var prev = $('<span class="prev-item form-nav-item"><a title="prev: '+ title +'" href="#">'+ title +'</a></span>');
                nav.append(prev);
                prev.find('a').click(function(){ prev_tab.find('a').click()});
            }
            if (next_tab !== null){
                var title = next_tab.find('a span').html();
                if (title !== undefined){
                    var next = $('<span class="next-item form-nav-item"><a title="next: '+ title +'" href="#">'+ title +'</a></span>');
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
            var extras = [];

            var extras_in = $('[name^="extras__"]');
            $.each(extras_in, function(idx, elm){
                var parent_elm = $(elm).parents(parent_name);
                if (parent_elm.length>0 && $.inArray(parent_elm[0], extras) < 0){
                    extras.push(parent_elm[0]);
                }
            });
            $.each(extras, function(idx, elm){
                form.append(elm);
            });
        },

        add_tab: function(tabs_container, container, tab_id, name, fields){
            var tab = $('<li class="nav-item"><a href="#' + tab_id + '-tab-container"><span>'+ name +'</span></a></li>');
            var form_p = $('<div id="'+ tab_id+'-tab-container"></div>');
            var that = this;
            tabs_container.append(tab);
            container.append(form_p);

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
