/** 

 Handles conforms to data edition.




*/
ckan.module('dcatapit-conforms-to', function($){
    return {
        initialize: function(){
            $.proxyAll(this, /_on/);
            var val = $.parseJSON($(this.el).val() || '[]');

            this.lang = this.options.lang;
            this.tmpl = $(this.options.template);
            this.container = $(this.options.container);
            this.val = val;

            this.localized = ['title', 'description'];


            this.populate_items(this.val, this.tmpl, this.container);
            this.add_handlers($(this.el).parent());
            this.add_form_handlers($(this.el.parent()));
        },

        /** 
            add submit event handler to disable input elements for elm
        */
        add_form_handlers: function(elm){
            elm.parents('form').submit(
                function(){
                        var inputs = $('.conforms_to input', elm);
                        inputs.attr('disabled', true);
                        $('input[name=conforms_to]', elm).attr('disabled', false);
                   }
                 )
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
                     and add callbacks for inputs to update conforms_to after change
                */
                var h = function(evt){
                    var t = that.add_row(tmpl, elm, []);
                }
                add_with.data('has-container-cb', true);

                $('input', ctx).each(function(iidx, ielm){
                        var ch = function(evt){
                                that.extract_values();
                         }
                        $(ielm).change(ch);
                    });

                add_with.click(h);
            });
        },

        add_row: function(template, container, values){
            var t = template.clone(true).removeClass('template');

            container.append(t[0]);
            this.add_values(t, values);
            this.add_handlers(t);
            return t;
        },

        add_values: function(ui, values){
            for (var k in values){
                var val = values[k];
                var input_name = 'conforms_to_' + k;

                if (k == 'referenceDocumentation'){
                    
                    var refdoc_ui = $('.reference_documentation.template', ui);
                    var refdocs_container = $('.reference_container', ui);

                    for (var i = 0; i< val.length; i++){
                        var refdoc_val = val[i];
                        var to_add = refdoc_ui.clone().removeClass('template');
                        refdocs_container.append(to_add);
                        to_add.val(refdoc_val);

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
            ui.data('conforms-to', values);
        },

        populate_items: function(values, template, tmpl_container){
            //clear container
            tmpl_container.html('');

            for (var i=0; i< values.length; i++){
                var value = values[i];
                this.add_row(template, tmpl_container, value);

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
                    if ($.inArray(elm_name, that.localized)> -1){
                        if (!$.isPlainObject(out[elm_name])){
                        out[elm_name] = {};
                        }
                        var elval = elm.val();
                        if (elval !== ""){
                            out[elm_name][that.lang] = elval;
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
