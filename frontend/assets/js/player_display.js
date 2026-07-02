/**
 * Player Display Layer — UI normalization only (no API / DB changes).
 * Ensures one unified view model and safe rendering across player surfaces.
 */
(function (global) {
    'use strict';

    function escapeHtml(value) {
        if (value == null) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function dedupePlayersById(players) {
        const seen = new Map();
        (players || []).forEach(function (p) {
            if (p && p.id != null && !seen.has(p.id)) {
                seen.set(p.id, p);
            }
        });
        return Array.from(seen.values());
    }

    function computeAge(dateOfBirth) {
        if (!dateOfBirth) return null;
        const dob = new Date(dateOfBirth);
        if (isNaN(dob.getTime())) return null;
        const today = new Date();
        let age = today.getFullYear() - dob.getFullYear();
        const m = today.getMonth() - dob.getMonth();
        if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
        return age >= 0 ? age : null;
    }

    function resolveInstitutionType(roleOrType) {
        const r = (roleOrType || '').toLowerCase();
        if (r.includes('club')) return 'Club';
        if (r.includes('academy')) return 'Academy';
        if (r.includes('school')) return 'School';
        if (r) return r.charAt(0).toUpperCase() + r.slice(1);
        return 'Institution';
    }

    function teamOwnership(raw, context) {
        if (raw.team && raw.team.name) {
            return {
                name: raw.team.name,
                type: raw.team.type || resolveInstitutionType(context && context.institutionType)
            };
        }
        if (raw.institution_name) {
            return {
                name: raw.institution_name,
                type: raw.institution_type || resolveInstitutionType(context && context.institutionType)
            };
        }
        if (context && context.institutionName) {
            return {
                name: context.institutionName,
                type: resolveInstitutionType(context.institutionType)
            };
        }
        return { name: 'Not Assigned', type: '' };
    }

    function computeStatus(raw) {
        const injury = String(raw.injury_status || 'None').toLowerCase();
        const fitness = String(raw.fitness_status || 'Fit').toLowerCase();
        const explicit = String(raw.status || '').toLowerCase();

        if (explicit.includes('suspend')) {
            return { label: 'Suspended', badgeClass: 'badge-danger', tone: 'danger' };
        }
        if (injury !== 'none' && injury !== '') {
            return { label: 'Injured', badgeClass: 'badge-danger', tone: 'danger' };
        }
        if (fitness.includes('injured') || fitness.includes('unfit')) {
            return { label: 'Injured', badgeClass: 'badge-danger', tone: 'danger' };
        }
        if (fitness.includes('recover')) {
            return { label: 'Recovering', badgeClass: 'badge-warning', tone: 'warning' };
        }
        return { label: 'Active', badgeClass: 'badge-success', tone: 'success' };
    }

    const DEFAULT_AVATAR = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTIwIDIxdi0yYTQgNCAwIDAgMC00LTRINGE0IDQgMCAwIDAtNCA0djIiLz48Y2lyY2xlIGN4PSIxMiIgY3k9IjciIHI9IjQiLz48L3N2Zz4=";
    const DEFAULT_LOGO = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDIyczgtNCA4LTEwVjVsLTgtMy04IDN2N2MwIDYgOCAxMCA4IDEweiIvPjwvc3ZnPg==";

    function isValidImageUrl(url) {
        if (url === null || url === undefined) return false;
        var s = String(url).trim();
        if (s === '' || s === 'null' || s === 'undefined' || s === 'None' || s === ' ' || s === 'None') return false;
        // data: URIs are always valid (our base64 fallbacks)
        if (s.indexOf('data:') === 0) return true;
        // Must have a file extension or be a URL path
        if (s.indexOf('/') >= 0 || s.indexOf('.') >= 0 || s.indexOf('\\') >= 0) return true;
        return false;
    }

    function normalizePhotoUrl(url) {
        if (url === null || url === undefined) return DEFAULT_AVATAR;
        var s = String(url).trim();
        if (s === '' || s === 'null' || s === 'undefined' || s === 'None' || s === ' ') return DEFAULT_AVATAR;
        
        // Normalize backslashes to forward slashes
        s = s.replace(/\\/g, '/');

        if (s.indexOf('data:') === 0) return s;
        if (s.indexOf('http://') === 0 || s.indexOf('https://') === 0) return s;
        
        // If it contains assets/uploads/
        if (s.indexOf('assets/uploads/') >= 0) {
            var parts = s.split('assets/uploads/');
            return '/assets/uploads/' + parts[parts.length - 1];
        }
        // If it contains uploads/ but not assets/
        if (s.indexOf('uploads/') >= 0) {
            var parts = s.split('uploads/');
            return '/assets/uploads/' + parts[parts.length - 1];
        }
        // If it is just a filename
        if (s.indexOf('/') === -1) {
            return '/assets/uploads/' + s;
        }
        // Ensure leading slash
        if (s.charAt(0) !== '/') {
            s = '/' + s;
        }
        return s;
    }

    /**
     * Unified player view model for display (required + optional fields).
     */
    function normalizePlayer(raw, context) {
        if (raw && raw.raw) {
            raw = raw.raw;
        }
        var p = raw || {};
        var team = teamOwnership(p, context || {});
        var status = computeStatus(p);
        var age = p.age != null && p.age !== '' ? p.age : computeAge(p.date_of_birth);

        var rawPhoto = p.photo || p.photo_url;
        var photoUrl = normalizePhotoUrl(rawPhoto);

        var instLogo = p.institution_logo || p.logo_url || (p.institution && p.institution.logo_url) || (context && context.logoUrl);
        var logoUrl = isValidImageUrl(instLogo) ? instLogo : null;

        var clubLogo = (team.type === 'Club') ? (logoUrl || DEFAULT_LOGO) : DEFAULT_LOGO;
        var academyLogo = (team.type === 'Academy') ? (logoUrl || DEFAULT_LOGO) : DEFAULT_LOGO;
        var schoolLogo = (team.type === 'School') ? (logoUrl || DEFAULT_LOGO) : DEFAULT_LOGO;

        // Log missing fields or paths for debugging, prevent silent UI failures but don't show raw errors to users
        if (!rawPhoto) {
            console.warn(`[DATA INTEGRITY] Missing photo path for player: ${p.name || 'Unknown'} (ID: ${p.id || 'N/A'})`);
        }
        if (!instLogo) {
            console.warn(`[DATA INTEGRITY] Missing institution logo for team: ${team.name} (Type: ${team.type})`);
        }

        return {
            id: p.id,
            photo: photoUrl,
            photoUrl: photoUrl,
            fullName: p.name || 'Unknown Player',
            playerId: p.player_code || (p.id != null ? 'ID-' + p.id : '--'),
            position: p.position || '--',
            jerseyNumber: p.jersey_number != null && p.jersey_number !== '' ? p.jersey_number : '--',
            nationality: p.nationality || '--',
            teamName: team.name,
            teamType: team.type,
            teamLabel: team.type ? team.type + ': ' + team.name : team.name,
            dateOfBirth: p.date_of_birth || null,
            age: age != null ? age : '--',
            preferredFoot: p.preferred_foot || '--',
            statusLabel: status.label,
            statusBadgeClass: status.badgeClass,
            statusTone: status.tone,
            rating: p.rating,
            goals: p.goals,
            assists: p.assists,
            club: {
                logo: clubLogo
            },
            academy: {
                logo: academyLogo
            },
            school: {
                logo: schoolLogo
            },
            medical: {
                height: p.height,
                weight: p.weight,
                injuryStatus: p.injury_status || 'None',
                fitnessLevel: p.fitness_status || 'Fit',
                medicalNotes: p.medical_conditions || '',
                lastCheckup: p.last_medical_check || null,
                bloodGroup: p.blood_group || null
            },
            raw: p
        };
    }

    function photoHtml(photoUrl, sizePx) {
        var size = sizePx || 48;
        var safe = escapeHtml(photoUrl || DEFAULT_AVATAR);
        return (
            '<img src="' + safe + '" alt="" width="' + size + '" height="' + size + '" ' +
            'onerror="this.onerror=null; this.src=\'' + DEFAULT_AVATAR + '\';" ' +
            'style="width:' + size + 'px;height:' + size + 'px;border-radius:50%;object-fit:cover;border:3px solid #16A34A;box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
        );
    }

    function rowHtml(player, onView, onEdit, onMedical, onDelete, onTransfer) {
        var safe = function(str) { return escapeHtml(str || '--'); };
        
        // Status Badge Logic
        var badgeBg = '#DCFCE7';
        var badgeText = '#166534';
        var lbl = player.statusLabel || 'Active';
        var lLower = lbl.toLowerCase();
        
        if (lLower === 'injured') {
            badgeBg = '#FEE2E2';
            badgeText = '#991B1B';
        } else if (lLower === 'recovering') {
            badgeBg = '#FEF3C7';
            badgeText = '#92400E';
        } else if (lLower === 'suspended') {
            badgeBg = '#E2E8F0';
            badgeText = '#334155';
        }
        
        var statusBadge = '<span style="display:inline-block;padding:4px 8px;border-radius:4px;font-size:0.75rem;font-weight:700;background:' + badgeBg + ';color:' + badgeText + ';">' + safe(lbl) + '</span>';

        // Action Buttons
        var btnStyle = 'background:transparent;border:none;cursor:pointer;padding:4px 8px;border-radius:4px;color:#94A3B8;transition:color 0.2s;';
        
        var actionsHtml = '<div style="display:flex;gap:0.25rem;">';
        if (onView) actionsHtml += '<button title="View" style="' + btnStyle + '" onmouseover="this.style.color=\'#16A34A\'" onmouseout="this.style.color=\'#94A3B8\'" onclick="event.stopPropagation(); ' + escapeHtml(onView) + '"><i data-lucide="eye" style="width:18px;height:18px;"></i></button>';
        if (onEdit) actionsHtml += '<button title="Edit" style="' + btnStyle + '" onmouseover="this.style.color=\'#16A34A\'" onmouseout="this.style.color=\'#94A3B8\'" onclick="event.stopPropagation(); ' + escapeHtml(onEdit) + '"><i data-lucide="edit" style="width:18px;height:18px;"></i></button>';
        if (onMedical) actionsHtml += '<button title="Medical" style="' + btnStyle + '" onmouseover="this.style.color=\'#D97706\'" onmouseout="this.style.color=\'#94A3B8\'" onclick="event.stopPropagation(); ' + escapeHtml(onMedical) + '"><i data-lucide="heart-pulse" style="width:18px;height:18px;"></i></button>';
        if (onTransfer) actionsHtml += '<button title="Transfer" style="' + btnStyle + '" onmouseover="this.style.color=\'#16A34A\'" onmouseout="this.style.color=\'#94A3B8\'" onclick="event.stopPropagation(); ' + escapeHtml(onTransfer) + '"><i data-lucide="arrow-right-left" style="width:18px;height:18px;"></i></button>';
        if (onDelete) actionsHtml += '<button title="Delete" style="' + btnStyle + '" onmouseover="this.style.color=\'#DC2626\'" onmouseout="this.style.color=\'#94A3B8\'" onclick="event.stopPropagation(); ' + escapeHtml(onDelete) + '"><i data-lucide="trash-2" style="width:18px;height:18px;"></i></button>';
        actionsHtml += '</div>';

        // Row HTML
        var row = '<tr style="border-bottom:1px solid rgba(255,255,255,0.08);background:#1E293B;transition:background 0.2s;" onmouseover="this.style.background=\'#0F172A\'" onmouseout="this.style.background=\'#1E293B\'">';
        row += '<td style="padding:1rem;">' + photoHtml(player.photoUrl, 48) + '</td>';
        row += '<td style="padding:1rem;font-weight:600;color:#16A34A;">' + safe(player.playerId) + '</td>';
        row += '<td style="padding:1rem;font-weight:700;color:#FFFFFF;font-size:1.1rem;">' + safe(player.fullName) + '</td>';
        row += '<td style="padding:1rem;color:#94A3B8;">' + safe(player.dateOfBirth) + '</td>';
        row += '<td style="padding:1rem;color:#94A3B8;">' + safe(player.age) + '</td>';
        row += '<td style="padding:1rem;font-weight:600;color:#E2E8F0;">' + safe(player.position) + '</td>';
        row += '<td style="padding:1rem;color:#94A3B8;">' + safe(player.jerseyNumber) + '</td>';
        row += '<td style="padding:1rem;color:#94A3B8;">' + safe(player.nationality) + '</td>';
        row += '<td style="padding:1rem;font-weight:600;color:#E2E8F0;">' + safe(player.teamLabel) + '</td>';
        row += '<td style="padding:1rem;">' + statusBadge + '</td>';
        row += '<td style="padding:1rem;">' + actionsHtml + '</td>';
        row += '</tr>';

        return row;
    }

    function getDisplayContext() {
        return {
            institutionName: global.localStorage ? global.localStorage.getItem('institution_name') : null,
            institutionType: global.localStorage ? (global.localStorage.getItem('institution_type') || global.localStorage.getItem('role')) : null
        };
    }

    global.PlayerDisplay = {
        escapeHtml: escapeHtml,
        dedupePlayersById: dedupePlayersById,
        normalizePlayer: normalizePlayer,
        photoHtml: photoHtml,
        rowHtml: rowHtml,
        getDisplayContext: getDisplayContext,
        computeStatus: computeStatus,
        DEFAULT_AVATAR: DEFAULT_AVATAR,
        DEFAULT_LOGO: DEFAULT_LOGO
    };
})(typeof window !== 'undefined' ? window : this);
