/* https://github.com/capaj/react-tweet-embed/blob/master/tweet-embed.js */

import React from 'react'
import PropTypes from 'prop-types'

const callbacks = []

function addScript (src, cb) {
    if (callbacks.length === 0) {
        callbacks.push(cb)
        var s = document.createElement('script')
        s.setAttribute('src', src)
        s.onload = () => callbacks.forEach((cb) => cb())
        document.body.appendChild(s)
    } else {
        callbacks.push(cb)
    }
}


class TweetEmbed extends React.Component {
    componentDidMount () {
        const renderTweet = () => {
            window.twttr.ready().then(({ widgets }) => {
                const { options, onTweetLoadSuccess, onTweetLoadError, id } = this.props

                this._div.innerHTML = `
                    <blockquote class="twitter-tweet card-blockquote" data-dnt="true">
                        <div class="card custom-tweet">
                            <div class="card-block">
                                <header>
                                    <p class="twitter-user-name">${ this.props.user_name }</p>
                                        <small class="text-muted">@${ this.props.screen_name }</small>
                                </header>
                                            <blockquote class="card-blockquote">
                                                <p dir="ltr" lang="${ this.props.lang }" class="card-text">
                                                    ${this.props.text}
                                                </p>
                                                    <small>
                                                        <a href="https://twitter.com/${this.props.screen_name}/status/${id}">${this.props.created_at}</a>
                                                    </small>
                                            </blockquote>
                            </div>
                        </div>
                    </blockquote>
                `

                widgets.load(this._div)

                /* widgets*/
                /* .createTweet(this.props.id, this._div, options)*/
                /* .then(onTweetLoadSuccess)*/
                /* .catch(onTweetLoadError)*/

            })
        }

        if (!window.twttr) {
            const isLocal = window.location.protocol.indexOf('file') >= 0
            const protocol = isLocal ? this.props.protocol : ''

            addScript(`${protocol}//platform.twitter.com/widgets.js`, renderTweet)
        } else {
            renderTweet()
        }
    }

    render () {
        return <div className={this.props.className} ref={(c) => {
                this._div = c
        }} />
    }
}

TweetEmbed.propTypes = {
    id: PropTypes.string,
    options: PropTypes.object,
    protocol: PropTypes.string,
    onTweetLoadSuccess: PropTypes.func,
    onTweetLoadError: PropTypes.func,
    className: PropTypes.string,
    user_name: PropTypes.string,
    screen_name: PropTypes.string,
    lang: PropTypes.string,
    text: PropTypes.string,
    created_at: PropTypes.string
}

TweetEmbed.defaultProps = {
    protocol: 'https:',
    options: {},
    className: null
}

export default TweetEmbed
