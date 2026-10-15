# d3 MCP Capability Map

Use this as a routing table from friendly d3 media-server requests to the d3service tools. Some hosts add a prefix to the tool names (for example `mcp__d3service__`).

**The names come from `tools/list`.** This file is a hint. The list of tools changes with the software version. If a name below is not in `tools/list`, use the name that `tools/list` gives.

## GUI Screenshots

- `internal_gui_capture` — capture the current GUI feed/space view and return it as an **inline image** (base64 PNG in the tool result). Params: `width`, `height`, `widgets` (include GUI widgets; default false = feed/space only). This is the primary way to see what d3 is rendering — no file paths, shared drives, or polling. It captures the *current* editor view; for a controlled third-person overview from a specific camera pose, use the `capture_stage()` Python helper instead (see `references/visual-verification.md`).

## Status, Project, System, Network

- Session/project: `status_get_session`, `status_get_project`, `service_system_list_projects`.
- Health/notifications: `status_list_health`, `status_list_notifications`.
- GUI mode: `status_set_gui_mode`.
- Looks: `looks_list`.
- Project lifecycle: `service_project_start_local`, `service_project_quit_local`, `service_project_restart_local`, `service_project_force_quit_local`.
- Diagnostics and machine info: `service_system_detect`, `service_system_get_os_info`, `service_system_create_system_diagnostics`, `service_system_create_project_diagnostics`.
- Hardware/system: `service_system_get_network_adapters`, `service_system_get_vfcs`, `service_system_get_gpu_outputs`, `service_system_post_boot_running`.
- Remote config/network: `service_remote_config_hostname`, `service_remote_config_get_this_machine`, `service_remote_config_get_available_machines`, `service_remote_config_adapter_list`, `service_remote_config_get_adapter`, `service_remote_config_get_default_adapter`, `service_remote_config_set_default_adapter`, `service_remote_config_dhcp_enabled`, `service_remote_config_static_ip`.

## Notes and Transport

- Notes: `notes_list`, `notes_get`, `notes_set`.
- Transport discovery: `transport_list`, `transport_get_active`, `transport_list_tracks`, `transport_list_set_lists`, `transport_list_cues`, `transport_list_annotations`.
- Transport playback: `transport_play`, `transport_stop`, `transport_return_to_start`, `transport_play_section`, `transport_play_loop_section`.
- Transport jumps: `transport_go_to_time`, `transport_go_to_time_code`, `transport_go_to_frame`, `transport_go_to_track`, `transport_go_to_prev_track`, `transport_go_to_next_track`, `transport_go_to_section`, `transport_go_to_prev_section`, `transport_go_to_next_section`, `transport_go_to_note`, `transport_go_to_tag`.
- Keyframe jumps: `transport_go_to_next_keyframe`, `transport_go_to_prev_keyframe`.
- Transport state: `transport_set_volume`, `transport_set_brightness`, `transport_set_speed`, `transport_set_engaged`.
- Transport-control v1 (UID-addressed). Use these when a request needs UID-addressed transports, tracks, setlists, sections, cues, output mode, fade up/down, or hold:
  - Read: `transport_control_list_transports`, `transport_control_get_transport`, `transport_control_get_transport_status`, `transport_control_list_tracks`, `transport_control_get_track`, `transport_control_list_setlists`, `transport_control_get_setlist`, `transport_control_list_sections`, `transport_control_list_cues`, `transport_control_get_output_mode`.
  - Playback: `transport_control_play_transport`, `transport_control_stop_transport`, `transport_control_return_to_start`, `transport_control_play_section_transport`, `transport_control_loop_section_transport`, `transport_control_hold`.
  - Jumps: `transport_control_go_to_track`, `transport_control_next_track`, `transport_control_previous_track`, `transport_control_next_section`, `transport_control_previous_section`, `transport_control_go_to_cue`, `transport_control_go_to_cue_name`, `transport_control_go_to_time_code`.
  - State: `transport_control_set_transport_status`, `transport_control_set_volume`, `transport_control_set_brightness`, `transport_control_engage`, `transport_control_disengage`, `transport_control_fade_up`, `transport_control_fade_down`.

## Media, Content, Resources

- Media metadata: `content_list_media_metadata`, `content_get_media_metadata`, `internal_media_get`.
- Local media/files: `service_media_get`, `service_media_provision`, `service_media_remove`, `internal_media_remove`.
- Remote sources: `service_content_sources_list_remote_sources`, `service_content_sources_get_remote_source`, `service_content_sources_create_remote_source`, `service_content_sources_edit_remote_source`, `service_content_sources_delete_remote_source`, `service_content_sources_connect_remote_source`, `service_content_sources_list_remote_source_files`.
- Content tasks: `content_tasks_list_tasks`, `content_tasks_create_task`, `content_tasks_run_task`, `content_tasks_cancel_task`, `content_tasks_reset_task`, `content_tasks_delete_task`.
- Content usage: `content_usage_list_missing_media`, `content_usage_sync_missing_media`, `content_usage_list_unused_media_copies`.
- Resources and thumbnails: `resources_list`, `resources_get`, `thumbnails_get`.
- Indirections/sequencing: `indirections_list`, `indirections_get`, `indirections_set`, `sequencing_list_indirections`, `sequencing_list_available_resources`, `sequencing_change_indirections`.

## RenderStream and Failover

- Legacy/session RenderStream: `render_stream_get_pools`, `render_stream_get_layers`, `render_stream_get_assigners`, `render_stream_get_layer_config`, `render_stream_get_layer_status`, `render_stream_start_layers`, `render_stream_stop_layers`, `render_stream_restart_layers`, `render_stream_sync_layers`, `render_stream_failover`, `render_stream_failover_pool`.
- v1 RenderStream: `renderstream_list_clusters`, `renderstream_get_cluster`, `renderstream_list_workloads`, `renderstream_get_workload`, `renderstream_start_workload`, `renderstream_stop_workload`, `renderstream_sync_workload`, `renderstream_list_render_machines`, `renderstream_get_render_machine`, `renderstream_get_workload_instance`, `renderstream_failover_render_machine`, `renderstream_failover_workload_instance`.
- Failover: `failover_get_failover_settings`, `failover_list_understudy_targets`, `failover_machine`, `failover_restore_machine`, `failover_apply_matrix_feed_routing`.

## Colour, Sockpuppet, Python, Shot Recorder

- Colour/CDL: `colour_list_cdls`, `colour_get_cdl`, `colour_set_cdl`.
- Sockpuppet/live changes: `sockpuppet_list_patches`, `sockpuppet_live_change`, `sockpuppet_list_easing_functions`.
- Python: `python_execute`, `python_register_module`.
- Shot recorder: `shot_recorder_list_recorders`, `shot_recorder_record_shot`.

## Mixed Reality, Calibration, QuickCal, OmniCal

- Mixed Reality: `mixed_reality_get_mr_sets`, `mixed_reality_list_spatial_calibrations`, `mixed_reality_get_cameras`, `mixed_reality_capture_observation`, `mixed_reality_capture_progress`, `mixed_reality_delete_observations`, `mixed_reality_delete_all_observations`, `mixed_reality_enable_observations`, `mixed_reality_select_camera`, `mixed_reality_select_spatial_calibration`.
- Camera calibration: `camera_calibration_list_mr_sets`, `camera_calibration_get_mr_set`, `camera_calibration_add_observation`, `camera_calibration_reset_all_observations`, `camera_calibration_enable_observation`, `camera_calibration_get_observation_progress`.
- QuickCal: `quickcal_list_reference_points`, `quickcal_get_projector_calibration`, `quickcal_reset_line_up`, `quickcal_line_up_current_pose`, `quickcal_overwrite_manual_calibration`.
- OmniCal: `omnical_current_plan`, `omnical_plans`, `omnical_camera_discovery`, `omnical_set_camera_discovery`, `omnical_execute_plan`, `omnical_current_result`, `omnical_results`, `omnical_results_for_plan`, `omnical_current_fallback_result`, `omnical_accept_result`, `omnical_check_result`, `omnical_revert_result`, `omnical_delete_old_results`.

## Internal and Advanced

- Telemetry: `internal_telemetry_trace_telemetry_event`, `internal_telemetry_feedback_telemetry_event`.
- NMOS: `internal_nmos_update_connection_sender`, `internal_nmos_set_receivers_sender_sdp`.
- OS imaging/reimage/deployment: `service_system_add_os_image`, `service_system_reimage_server`, `service_system_set_deployment_share`.
