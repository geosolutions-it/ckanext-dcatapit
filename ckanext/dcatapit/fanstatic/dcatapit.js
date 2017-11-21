
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

        },
        bind_evt: function(elm, container, tmpl){
            that = this;
            var h = function(evt){
                            that.add_new(evt, container, tmpl)}
            elm.click(h);

        },

        add_new: function(evt, container, template){
            var elm = $(evt.delegateTarget);
            if (!$(elm).hasClass('add_new')){
                return;
            }
            var _add = container.find('span.add_new').remove();
            container.append(this.get_template(template));
            container.append(_add);

            // need to rebind, because we've removed that element from dom
            this.bind_evt(_add, container, template);
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
            var val = $.parseJson(this.el.value);
        },
        populate_items: function(value, template, root){

        },
        extract_items: function(root){

        }
     }
    });
