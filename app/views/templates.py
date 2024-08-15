import traceback
import logging

from app                                              import app
from app.backend                                      import pkg
from app.backend.errors                               import ErrorMessages
from app.backend.components.templates.template_config import TemplateConfig
from app.backend.components.prompts.prompt_config     import PromptConfig
from app.backend.components.nfrs.nfr_config           import NFRConfig
from flask                                            import render_template, request, url_for, redirect, flash, jsonify


@app.route('/templates', methods=['GET', 'POST'])
def get_templates():
    try:
        project                 = request.cookies.get('project')
        templates               = TemplateConfig.get_all_templates(project)
        template_groups         = TemplateConfig.get_all_template_groups(project)
        nfrs                    = NFRConfig.get_all_nfrs(project)
        prompt_obj              = PromptConfig(project)
        template_prompts        = prompt_obj.get_prompts_by_place("template")
        aggregated_data_prompts = prompt_obj.get_prompts_by_place("aggregated_data")
        template_group_prompts  = prompt_obj.get_prompts_by_place("template_group")
        return render_template('home/templates.html', templates=templates, template_groups=template_groups, nfrs=nfrs, template_prompts=template_prompts, aggregated_data_prompts=aggregated_data_prompts, template_group_prompts=template_group_prompts)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.TEMPLATES.value, "error")
        return redirect(url_for("index"))

@app.route('/template', methods=['GET', 'POST'])
def template():
    try:
        project                 = request.cookies.get('project')
        graphs                  = pkg.get_config_names_and_ids(project, "graphs")
        nfrs                    = pkg.get_config_names_and_ids(project, "nfrs")
        prompt_obj              = PromptConfig(project)
        template_prompts        = prompt_obj.get_prompts_by_place("template")
        aggregated_data_prompts = prompt_obj.get_prompts_by_place("aggregated_data")
        system_prompts          = prompt_obj.get_prompts_by_place("system")
        template_config         = request.args.get('template_config')
        template_data           = []
        if template_config is not None:
            template_data = TemplateConfig.get_template_config_values(project, template_config)
        if request.method == "POST":
            try:
                original_template_config = request.get_json().get("id")
                template_config          = TemplateConfig.save_template_config(project, request.get_json())
                if original_template_config == template_config:
                    flash("Template updated.","info")
                else:
                    flash("Template added.","info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_TEMPLATE.value, "error")
            return jsonify({'redirect_url': 'templates'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_TEMPLATE.value, "error")
        return redirect(url_for("get_templates"))
    return render_template('home/template.html', template_config=template_config, graphs=graphs, nfrs=nfrs, template_data=template_data, template_prompts=template_prompts, aggregated_data_prompts=aggregated_data_prompts, system_prompts=system_prompts)

@app.route('/delete-template', methods=['GET'])
def delete_template():
    try:
        template_config = request.args.get('template_config')
        project         = request.cookies.get('project')
        if template_config is not None:
            TemplateConfig.delete_template_config(project, template_config)
            flash("Template is deleted.","info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DEL_TEMPLATE.value, "error")
    return redirect(url_for("get_templates"))

@app.route('/template-group', methods=['GET', 'POST'])
def template_group():
    try:
        project                = request.cookies.get('project')
        templates              = pkg.get_config_names_and_ids(project, "templates")
        template_group_config  = request.args.get('template_group_config')
        prompt_obj             = PromptConfig(project)
        template_group_prompts = prompt_obj.get_prompts_by_place("template_group")
        template_group_data    = []
        if template_group_config is not None:
            template_group_data = TemplateConfig.get_template_group_config_values(project, template_group_config)
        if request.method == "POST":
            try:
                original_template_group_config = request.get_json().get("id")
                template_group_config          = TemplateConfig.save_template_group_config(project, request.get_json())
                if original_template_group_config == template_group_config:
                    flash("Template group updated.","info")
                else:
                    flash("Template group added.","info")
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.SAVE_TEMPLATE_GROUP.value, "error")
            return jsonify({'redirect_url': 'templates'})
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.GET_TEMPLATE_GROUP.value, "error")
        return redirect(url_for("get_templates"))
    return render_template('home/template-group.html', template_group_config=template_group_config,templates=templates, template_group_data=template_group_data, template_group_prompts=template_group_prompts)

@app.route('/delete-template-group', methods=['GET'])
def delete_template_group():
    try:
        template_group_config = request.args.get('template_group_config')
        project               = request.cookies.get('project')
        if template_group_config is not None:
            TemplateConfig.delete_template_group_config(project, template_group_config)
            flash("Template group is deleted.","info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.DEL_TEMPLATE_GROUP.value, "error")
    return redirect(url_for("get_templates"))