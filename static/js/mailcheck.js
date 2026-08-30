/* globals define, module, jQuery */

/*
 * Mailcheck https://github.com/mailcheck/mailcheck
 * Author
 * Derrick Ko (@derrickko)
 *
 * Released under the MIT License.
 *
 * v 1.1.2
 */

var Mailcheck = {
  domainThreshold: 2,
  secondLevelThreshold: 2,
  topLevelThreshold: 2,

  defaultDomains: ['msn.com', 'bellsouth.net',
    'telus.net', 'comcast.net', 'optusnet.com.au',
    'earthlink.net', 'qq.com', 'sky.com', 'icloud.com',
    'mac.com', 'sympatico.ca', 'googlemail.com',
    'att.net', 'xtra.co.nz', 'web.de',
    'cox.net', 'gmail.com', 'ymail.com',
    'aim.com', 'rogers.com', 'verizon.net',
    'rocketmail.com', 'google.com', 'optonline.net',
    'sbcglobal.net', 'aol.com', 'me.com', 'btinternet.com',
    'charter.net', 'shaw.ca', 'proton.me', 'protonmail.com'],

  defaultSecondLevelDomains: ["yahoo", "hotmail", "mail", "live", "outlook", "gmx", "proton"],

  defaultTopLevelDomains: ["com", "com.au", "com.tw", "ca", "co.nz", "co.uk", "de",
    "fr", "it", "ru", "net", "org", "edu", "gov", "jp", "nl", "kr", "se", "eu",
    "ie", "co.il", "us", "at", "be", "dk", "hk", "es", "gr", "ch", "no", "cz",
    "in", "net", "net.au", "info", "biz", "mil", "co.jp", "sg", "hu", "uk", "me", "io", "app"],

  run: function(opts) {
    opts.domains = opts.domains || Mailcheck.defaultDomains;
    opts.secondLevelDomains = opts.secondLevelDomains || Mailcheck.defaultSecondLevelDomains;
    opts.topLevelDomains = opts.topLevelDomains || Mailcheck.defaultTopLevelDomains;
    opts.distanceFunction = opts.distanceFunction || Mailcheck.sift4Distance;

    var defaultCallback = function(result){ return result; };
    var suggestedCallback = opts.suggested || defaultCallback;
    var emptyCallback = opts.empty || defaultCallback;

    var result = Mailcheck.suggest(Mailcheck.encodeEmail(opts.email), opts.domains, opts.secondLevelDomains, opts.topLevelDomains, opts.distanceFunction);

    return result ? suggestedCallback(result) : emptyCallback();
  },

  suggest: function(email, domains, secondLevelDomains, topLevelDomains, distanceFunction) {
    email = email.toLowerCase();

    var emailParts = this.splitEmail(email);

    if (secondLevelDomains && topLevelDomains) {
        // If the email is a valid 2nd-level + top-level, do not suggest anything.
        if (secondLevelDomains.indexOf(emailParts.secondLevelDomain) !== -1 && topLevelDomains.indexOf(emailParts.topLevelDomain) !== -1) {
            return false;
        }
    }

    var closestDomain = this.findClosestDomain(emailParts.domain, domains, distanceFunction, this.domainThreshold);

    if (closestDomain) {
      if (closestDomain == emailParts.domain) {
        // The email address exactly matches one of the supplied domains; do not return a suggestion.
        return false;
      } else {
        // The email address closely matches one of the supplied domains; return a suggestion
        return { address: emailParts.address, domain: closestDomain, full: emailParts.address + "@" + closestDomain };
      }
    }

    // The email address does not closely match one of the supplied domains
    var closestSecondLevelDomain = this.findClosestDomain(emailParts.secondLevelDomain, secondLevelDomains, distanceFunction, this.secondLevelThreshold);
    var closestTopLevelDomain    = this.findClosestDomain(emailParts.topLevelDomain, topLevelDomains, distanceFunction, this.topLevelThreshold);

    if (emailParts.domain) {
      closestDomain = emailParts.domain;
      var rdone = false;

      if(closestSecondLevelDomain && closestSecondLevelDomain != emailParts.secondLevelDomain) {
        // The email address may have a mispelled 2nd-level domain; replace with closest
        closestDomain = closestDomain.replace(emailParts.secondLevelDomain, closestSecondLevelDomain);
        rdone = true;
      }

      if(closestTopLevelDomain && closestTopLevelDomain != emailParts.topLevelDomain) {
        // The email address may have a mispelled top-level domain; replace with closest
        closestDomain = closestDomain.replace(new RegExp(emailParts.topLevelDomain + '$'), closestTopLevelDomain);
        rdone = true;
      }

      if (rdone) {
        return { address: emailParts.address, domain: closestDomain, full: emailParts.address + "@" + closestDomain };
      }
    }

    return false;
  },

  findClosestDomain: function(domain, domains, distanceFunction, threshold) {
    threshold = threshold || this.topLevelThreshold;
    var dist;
    var minDist = 99;
    var closestDomain = null;

    if (!domain || !domains) {
      return false;
    }
    if(!distanceFunction) {
      distanceFunction = this.sift4Distance;
    }

    for (var i = 0; i < domains.length; i++) {
      if (domain === domains[i]) {
        return domain;
      }
      dist = distanceFunction(domain, domains[i]);
      if (dist < minDist) {
        minDist = dist;
        closestDomain = domains[i];
      }
    }

    if (minDist <= threshold && closestDomain !== null) {
      return closestDomain;
    } else {
      return false;
    }
  },

  sift4Distance: function(s1, s2, maxOffset) {
    // Sift4 - common substring distance algorithm
    maxOffset = maxOffset || 5;
    if (!s1 || !s1.length) {
      if (!s2 || !s2.length) {
        return 0;
      }
      return s2.length;
    }
    if (!s2 || !s2.length) {
      return s1.length;
    }

    var l1 = s1.length;
    var l2 = s2.length;

    var c1 = 0;
    var c2 = 0;
    var lcss = 0;
    var local_cs = 0;
    var trans = 0;
    var offset_arr = [];

    while ((c1 < l1) && (c2 < l2)) {
      if (s1.charAt(c1) == s2.charAt(c2)) {
        local_cs++;
        var isTrans = false;
        var i = 0;
        while (i < offset_arr.length) {
          var ofs = offset_arr[i];
          if (c1 <= ofs.c1 || c2 <= ofs.c2) {
            isTrans = Math.abs(c2 - c1) >= Math.abs(ofs.c2 - ofs.c1);
            if (isTrans) {
              trans++;
            }
            break;
          } else {
            if (c1 > ofs.c1 && c2 > ofs.c2) {
              offset_arr.splice(i, 1);
            } else {
              i++;
            }
          }
        }
        offset_arr.push({
          c1: c1,
          c2: c2
        });
      } else {
        lcss += local_cs;
        local_cs = 0;
        if (c1 != c2) {
          c1 = Math.min(c1, c2);
          c2 = c1;
        }
        for (var i = 0; i < maxOffset; (i++)) {
          if ((c1 + i < l1) && (s1.charAt(c1 + i) == s2.charAt(c2))) {
            c1 += i - 1;
            c2--;
            break;
          }
          if ((c2 + i < l2) && (s1.charAt(c1) == s2.charAt(c2 + i))) {
            c1--;
            c2 += i - 1;
            break;
          }
        }
      }
      c1++;
      c2++;
    }
    lcss += local_cs;
    return Math.round(Math.max(l1, l2) - lcss + trans);
  },

  splitEmail: function(email) {
    email = (email || '').trim().toLowerCase();
    var parts = email.split('@');

    if (parts.length < 2) {
      return false;
    }

    for (var i = 0; i < parts.length; i++) {
      if (parts[i] === '') {
        return false;
      }
    }

    var domain = parts.pop();
    var domainParts = domain.split('.');
    var sld = '';
    var tld = '';

    if (domainParts.length === 0) {
      // The address does not have a top-level domain
      return false;
    } else if (domainParts.length == 1) {
      // The address has only a top-level domain (e.g. localhost)
      tld = domainParts[0];
    } else {
      // The address has a domain and a top-level domain
      sld = domainParts[0];
      tld = domainParts.slice(1).join('.');
    }

    return {
      topLevelDomain: tld,
      secondLevelDomain: sld,
      domain: domain,
      address: parts.join('@')
    };
  },

  encodeEmail: function(email) {
    var result = encodeURI(email);
    result = result.replace('%20', ' ').replace('%25', '%').replace('%5E', '^')
                   .replace('%60', '`').replace('%7B', '{').replace('%7C', '|')
                   .replace('%7D', '}');
    return result;
  },

  attach: function(inputSelector, containerSelector, buttonSelector) {
    var input = typeof inputSelector === 'string' ? document.querySelector(inputSelector) : inputSelector;
    var container = typeof containerSelector === 'string' ? document.querySelector(containerSelector) : containerSelector;
    var button = typeof buttonSelector === 'string' ? document.querySelector(buttonSelector) : buttonSelector;
    if (!input) return;

    function setButtonState(disabled) {
      if (!button) return;
      button.disabled = disabled;
      if (disabled) {
        button.classList.add('opacity-40', 'cursor-not-allowed', 'pointer-events-none');
      } else {
        button.classList.remove('opacity-40', 'cursor-not-allowed', 'pointer-events-none');
      }
    }

    function check() {
      var val = input.value.trim();
      Mailcheck.run({
        email: val,
        suggested: function(suggestion) {
          if (container) {
            container.innerHTML = 'Did you mean <button type="button" class="underline text-amber-400 font-bold hover:text-amber-300 transition-colors pointer-events-auto" data-mailcheck-suggest="' + suggestion.full + '">' + suggestion.full + '</button>?';
            container.classList.remove('hidden');
            setButtonState(true);
            var btn = container.querySelector('[data-mailcheck-suggest]');
            if (btn) {
              btn.onclick = function(e) {
                if (e) e.preventDefault();
                input.value = suggestion.full;
                container.classList.add('hidden');
                container.innerHTML = '';
                setButtonState(false);
                input.focus();
                if (typeof checkResetEmail === 'function') checkResetEmail();
                if (typeof applyMagicSuggestion === 'function') applyMagicSuggestion(suggestion.full);
              };
            }
          }
        },
        empty: function() {
          if (container) {
            container.classList.add('hidden');
            container.innerHTML = '';
            setButtonState(false);
          }
        }
      });
    }

    input.addEventListener('blur', check);
    input.addEventListener('input', function() {
      check();
    });
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = Mailcheck;
} else if (typeof define === 'function' && define.amd) {
  define(function() { return Mailcheck; });
} else {
  window.Mailcheck = Mailcheck;
}
