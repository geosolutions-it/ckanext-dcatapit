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
            var inputs = $('input', elms);
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
            var username = this.options.geonames-username;
            var limit_to = $.parseJSON(this.options.geonames-limit-to|| []);
            var el = $(this.el);
            jeoquery.defaultData.userName = username;
            el.jeoCityAutoComplete({'country': limit_to});

        },
    };
    return $.extend({}, geonames);
 });

