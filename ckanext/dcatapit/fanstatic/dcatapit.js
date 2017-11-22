
/**
    dcatapit-is-template is a way to make elements dynamically added

    markup:

    <div class="template" data-module="dcatapit-elm-template" data-module-container="#container">
        ...
    </div>

    <div id="container">

    </div>


    .template class will hide template markup, but each copy added to container, will have this class stripped, and
    will be a copy of template node

*/
ckan.module('dcatapit-elm-template', function($){
    return {
        initialize: function(){
            $.proxyAll(this, /_on/);

            if (!$(this.el).hasClass('template')){
                return;
            }
            var tmpl = this.get_template(this.el);
            var container = this.get_container(this.options.container);
            var _add = container.find('span.add_new');

            var that = this;

            this.bind_evt(_add, container, tmpl);
            $(this.el).data('elm-template', this);

        },
        on_container_change: function(evt, added){

        },
        bind_evt: function(elm, container, tmpl){
            that = this;
            var h = function(evt){
                     that.add_new(evt, container, tmpl)}
            elm.click(h);


        },

        add_new: function(evt, container, template){
            var _add = container.find('span.add_new').remove();
            var t = this.get_template(template)
            container.append(t);
            container.append(_add);
            this.on_container_change(evt, t);
            // need to rebind, because we've removed that element from dom
            this.bind_evt(_add, container, template);
            return t;
        },

        /**
            Returns template clone processed, ready to append to container
            @param root template element
        */
        get_template: function(t){
            return t.clone().removeClass('template');
        },
        
        /**
            Returns container element, where templates will be appended
            @param container jquery selector
        */
        get_container: function(container){
            var c = $(container);
            if (c.find('span.add_new').length < 1){
                c.append($('<span class="add_new"><i class="icon-plus"></i> Add new</span>'));
            };
            return c;
        }
     }
    });


ckan.module('dcatapit-conforms-to', function($){
    return {
        initialize: function(){
            $.proxyAll(this, /_on/);
            if (this.el.value){
                var val = $.parseJSON(this.el.value);
            } else {
                var val = [];
            };

            this.lang = this.options.lang;
            this.tmpl = $(this.options.template);
            this.container = $(this.options.container);
            this.val = val;
            this.populate_items(this.val, this.tmpl, this.container);


            this.add_handlers($(this.el).parent());
        },

        /** install onclick handlers for main templates
        */
        add_handlers: function(ctx){
            var that = this;
            $('.add_new_container', ctx).each(function(idx, elm){
                var add_with = $($(elm).data("add-with"));
                var tmpl = $($(elm).data('add-template'));

                var h = function(evt){
                    var t = tmpl.clone(true).removeClass('template');
                    elm.append(t[0]);
                    $('input', t).each(function(iidx, ielm){
                            var ch = function(evt){
                                    that.extract_values();
                             }
                            $(ielm).change(ch);
                        });
                }

                add_with.click(h);
            });
        },

        add_row: function(template, container, values){
            var t = template.clone(true).removeClass('template');
            container.append(t);
            this.add_values(t, values);

            this.add_handlers(t);
            return t;
        },

        add_values: function(template, values){
            for (var k in values){
                var val = values[k];

                if (k == 'referenceDocumentation'){
                    var refdoc_ui = $('.reference_documentation.template', template);
                    var refdocs_container = $('.reference_container', template);
                    for (var i = 0; i< val.length; i++){
                        var refdoc_val = refdocs[i];
                        var to_add = refdoc_ui.clone().removeClass('template');
                        refdoc_ui.val(refdoc_val);
                        refdocs_container.append(refdoc_ui);
                    }

                } else {
                    var local_val = val[this.lang];
                    ui.find('input[name=' + k + ']').val(local_val);
                    ui.attr('lang', this.lang);
                }
            }
            template.data('conforms-to', values);
        },

        populate_items: function(values, template, tmpl_container){
            //clear container
            tmpl_container.html('');

            for (var i=0; i< values.length; i++){
                var value = values[i];
                var ui = this.add_row(template, tmpl_container, value);

            }
        },

        extract_from_element: function(elms){
            var out = {};
            var existing = $(elms).data('conforms-to') || {};
            $.merge(out, existing);
            var lang = this.lang;
            var inputs = $('input', elms);
            var that = this;

            inputs.each(function(idx, elm){
                var elm = $(elm);
                var _elm_name = elm.attr('name');
                var elm_name = _elm_name.slice('conforms_to_'.length);

                if (elm_name != 'referenceDocumentation'){
                    if (!$.isPlainObject(out[elm_name])){
                        out[elm_name] = {};
                    }
                    var elval = elm.val();
                    if (elval !== ""){
                        out[elm_name][that.lang] = elval;
                    }
                } else {
                    if (!$.isArray(out[elm_name])){
                        out[elm_name] = [];
                    }
                    var elval = elm.val();
                    if (elval !== ""){
                        out[elm_name].push(elval);
                    }
                }
            });
            return out;
        },
        extract_values: function(){
            var out = [];
            var containers = $('.conforms_to', this.root);
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
    });
